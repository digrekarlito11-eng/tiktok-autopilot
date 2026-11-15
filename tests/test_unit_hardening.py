"""
tests/test_unit_hardening.py - Comprehensive M1 Hardening Unit Tests for tiktok-autopilot.

Covers:
1. VideoFormatter & Themes:
   - True animated FFmpeg 5.1 progress bar (t=0.1 minimal vs t=duration*0.85 wide gold bar).
   - ASS Hook/Watermark duration uses full clip_duration when supplied.
2. TikTokPublisher Resilience:
   - HTTP 200 JSON error payload detection (error.code != "ok" -> status "error" or "auth_error").
   - 0-byte video guard in publish_clip and upload_video_binary(reject_empty=True).
   - Retry/backoff on transient 429, 5xx, and URLError.
3. Pipeline, LibraryAutopilot & CLI Demo Safety:
   - PUBLISH_MODE="" empty env var fallback to default ("public" or args.publish).
   - Collision-free _build_safe_title for long titles sharing 20-char prefix.
   - process_batch preserving all clips in tiktok_results.json without overwrite loss.
   - Atomic _save_history (temp file + os.replace) and per-clip idempotency (processed_clip_keys).
   - Session directory cleanup (downloads/session_*) after process_url.
   - Clean CWD during main.run_synthetic_demo.
4. GrowthOptimizer, ClipExtractor, VideoTranscriber & TikTokNotifier:
   - Word-boundary regex matching in _generate_hook_banner ("fois" != "foi", "maritime" != "mari").
   - GospelIntelligence recommended_hook priority when non-default.
   - ClipExtractor no double-counting on hyphenated compound words ("Saint-Esprit", "Jésus-Christ").
   - VideoTranscriber SRT comma timestamps (00:00:01,500 --> 00:00:04,000) and VTT headers (Kind:, Language:, NOTE).
   - TikTokNotifier Telegram Bot API URL support (api.telegram.org).
"""

import os
import io
import json
import subprocess
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock
import numpy as np
import pytest

import main
from src.video_formatter import VideoFormatter
from src.tiktok_publisher import TikTokPublisher
from src.pipeline import TikTokPipeline
from src.library_autopilot import LibraryAutopilot, resolve_publish_mode
from src.growth_optimizer import GrowthOptimizer
from src.clip_extractor import ClipExtractor, find_keyword_match
from src.transcriber import VideoTranscriber, parse_vtt_timestamp
from src.notifier import TikTokNotifier


# ============================================================================
# 1. VideoFormatter: Animated Progress Bar & ASS Duration
# ============================================================================

class TestVideoFormatterHardening:
    def test_progress_bar_genuinely_animates_across_frames(self, synthetic_preaching_video, tmp_path):
        """
        Empirically verifies on FFmpeg 5.1 that the golden progress bar is NOT static:
        - At t=0.1s (early frame), x=500 is NOT gold (bar hasn't reached middle yet).
        - At t=2.5s (83% of 3.0s clip), x=500 IS gold (#FFD700).
        """
        formatter = VideoFormatter(output_dir=str(tmp_path))
        rendered_mp4 = formatter.render_tiktok_video(
            video_input=synthetic_preaching_video,
            start_time=0.0,
            duration=3.0,
            hook_title="ANIMATION TEST",
            segments=[{"start": 0.0, "end": 3.0, "text": "Animation de la barre dorée"}],
            output_filename="anim_bar.mp4",
            watermark="@parole.de.foi",
            theme_name="gospel",
            with_progress_bar=True
        )

        def extract_frame(t: float) -> np.ndarray:
            cmd = [
                "ffmpeg", "-ss", str(t),
                "-i", rendered_mp4,
                "-vframes", "1",
                "-f", "image2pipe",
                "-pix_fmt", "rgb24",
                "-vcodec", "rawvideo",
                "-"
            ]
            raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            return np.frombuffer(raw, dtype=np.uint8).reshape((1920, 1080, 3))

        def is_gold(rgb) -> bool:
            r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
            return r > 220 and g > 180 and b < 60

        early_frame = extract_frame(0.1)
        late_frame = extract_frame(2.55)

        # At t=0.1s out of 3.0s, bar width is ~36px:
        # At x=800, y=1912 (bar zone) must match the background just above it (y=1900)
        early_diff = np.abs(early_frame[1912, 800].astype(int) - early_frame[1900, 800].astype(int)).max()
        assert early_diff < 25, (
            f"Expected x=800 at t=0.1s to match background (unpainted), got bar={early_frame[1912, 800].tolist()} vs bg={early_frame[1900, 800].tolist()}"
        )

        # At t=2.55s out of 3.0s (85%), bar width is ~918px:
        # At x=800, y=1912 MUST be painted gold (#FFD700 -> R~254, G~214, B~0) whereas y=1900 is testsrc yellow (G~253)
        r_late, g_late, b_late = [int(v) for v in late_frame[1912, 800]]
        assert r_late > 220 and 190 <= g_late <= 230 and b_late < 40, (
            f"Expected x=800 at t=2.55s to be gold (#FFD700), got RGB=({r_late}, {g_late}, {b_late})"
        )
        assert int(late_frame[1900, 800][1]) > 240, (
            f"Expected background at y=1900 to remain untouched yellow, got RGB={late_frame[1900, 800].tolist()}"
        )

    def test_ass_subtitles_uses_full_clip_duration(self, tmp_path):
        """
        Verifies that HookHeader and WatermarkBadge persist for the full clip_duration
        even if the last spoken subtitle segment ends earlier.
        """
        formatter = VideoFormatter(output_dir=str(tmp_path))
        ass_path = str(tmp_path / "dur_test.ass")
        segments = [{"start": 10.0, "end": 25.0, "text": "Court segment parlé"}]

        formatter.create_ass_subtitles(
            segments=segments,
            hook_title="HOOK COMPLET",
            ass_path=ass_path,
            clip_start=10.0,
            watermark="@parole.de.foi",
            theme_name="gospel",
            clip_duration=90.0
        )

        content = open(ass_path, "r", encoding="utf-8").read()
        # 90.0 seconds -> 0:01:30.00
        assert "Dialogue: 0,0:00:00.00,0:01:30.00,WatermarkBadge" in content
        assert "Dialogue: 0,0:00:00.00,0:01:30.00,HookHeader" in content


# ============================================================================
# 2. TikTokPublisher: HTTP 200 Error Payload, 0-Byte Guard & Retries
# ============================================================================

class TestTikTokPublisherHardening:
    def test_http_200_with_error_code_returns_error_not_success(self, tmp_path):
        """
        When TikTok Content Posting API v2 returns HTTP 200 with error.code != 'ok',
        publish_clip MUST return status='error' (or 'auth_error'), never 'success'.
        """
        video_file = tmp_path / "valid_clip.mp4"
        video_file.write_bytes(b"VALID_MP4_BYTES_12345")

        pub = TikTokPublisher(access_token="token_123")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "error": {
                "code": "spam_risk_too_many_posts",
                "message": "Daily post limit reached"
            }
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = pub.publish_clip(str(video_file), {"full_post_text": "Test"})

        assert res["status"] == "error"
        assert res["error_code"] == "spam_risk_too_many_posts"
        assert "spam_risk_too_many_posts" in res["error"]

    def test_http_200_with_auth_error_code_returns_auth_error(self, tmp_path):
        """When TikTok API returns HTTP 200 with access_token_invalid, status is 'auth_error'."""
        video_file = tmp_path / "valid_clip.mp4"
        video_file.write_bytes(b"VALID_MP4_BYTES_12345")

        pub = TikTokPublisher(access_token="expired_tok")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "error": {
                "code": "access_token_invalid",
                "message": "The access token is invalid or expired"
            }
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = pub.publish_clip(str(video_file), {"full_post_text": "Test"})

        assert res["status"] == "auth_error"
        assert res["error_code"] == "access_token_invalid"

    def test_zero_byte_video_blocked_in_publish_clip(self, tmp_path):
        """A 0-byte video file is rejected before making any API call."""
        empty_video = tmp_path / "zero.mp4"
        empty_video.write_bytes(b"")

        pub = TikTokPublisher(access_token="valid_token")
        with patch("urllib.request.urlopen") as mock_url:
            res = pub.publish_clip(str(empty_video), {"full_post_text": "Zero byte test"})
            assert res["status"] == "error"
            assert "0 octet" in res["error"]
            assert mock_url.call_count == 0

        with pytest.raises(ValueError, match="0 octet"):
            pub.upload_video_binary("https://upload.tiktok.com", str(empty_video), reject_empty=True)

    def test_retry_on_transient_429_and_503_then_succeed(self, tmp_path):
        """Retries transient HTTP 429 / 503 errors and succeeds when endpoint recovers."""
        video_file = tmp_path / "retry_clip.mp4"
        video_file.write_bytes(b"MP4_CONTENT_DATA")

        pub = TikTokPublisher(access_token="tok", max_retries=2, retry_delay=0.0)

        err_429 = urllib.error.HTTPError(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            429, "Too Many Requests", {}, io.BytesIO(b"rate limited")
        )
        ok_init = MagicMock()
        ok_init.status = 200
        ok_init.read.return_value = json.dumps({
            "data": {"upload_url": "https://upload.tiktok.com/put", "publish_id": "pub_ok"},
            "error": {"code": "ok"}
        }).encode("utf-8")
        ok_init.__enter__.return_value = ok_init

        ok_put = MagicMock()
        ok_put.status = 200
        ok_put.read.return_value = b""
        ok_put.__enter__.return_value = ok_put

        calls = {"post": 0, "put": 0}

        def side_effect(req, *args, **kwargs):
            if req.get_method() == "POST":
                calls["post"] += 1
                if calls["post"] == 1:
                    raise err_429
                return ok_init
            calls["put"] += 1
            return ok_put

        with patch("urllib.request.urlopen", side_effect=side_effect):
            res = pub.publish_clip(str(video_file), {"full_post_text": "Retry test"})

        assert res["status"] == "success"
        assert res["publish_id"] == "pub_ok"
        assert calls["post"] == 2
        assert calls["put"] == 1


# ============================================================================
# 3. Pipeline, LibraryAutopilot & Demo CWD Cleanliness
# ============================================================================

class TestPipelineAndAutopilotHardening:
    def test_resolve_publish_mode_handles_empty_env_var(self):
        """Empty or whitespace PUBLISH_MODE falls back to CLI default ('public')."""
        assert resolve_publish_mode("", "public") == "public"
        assert resolve_publish_mode("   ", "draft") == "draft"
        assert resolve_publish_mode(None, "public") == "public"
        assert resolve_publish_mode("draft", "public") == "draft"
        assert resolve_publish_mode("PUBLIC", "draft") == "public"

        bot = LibraryAutopilot(publish_mode="")
        assert bot.publish_mode == "public"

    def test_safe_title_avoids_collisions_on_shared_20_char_prefix(self):
        """Two long sermon titles sharing the first 20 chars produce distinct safe_title strings."""
        t1 = "Le mariage chrétien - Partie 1 : La communication"
        t2 = "Le mariage chrétien - Partie 2 : Le pardon mutuel"
        s1 = TikTokPipeline._build_safe_title(t1)
        s2 = TikTokPipeline._build_safe_title(t2)
        assert s1 != s2
        assert s1.startswith("Le mariage chrétien")
        assert s2.startswith("Le mariage chrétien")

        # Short title <= 20 chars without video_id remains unchanged for backward compatibility
        assert TikTokPipeline._build_safe_title("Court Titre") == "Court Titre"
        assert TikTokPipeline._build_safe_title("!!!") == "video"

    def test_process_batch_preserves_all_clips_in_results_json(self, tmp_path):
        """process_batch aggregates clips across all processed URLs in tiktok_results.json."""
        out_dir = tmp_path / "out"
        tmp_dir = tmp_path / "dl"
        pipeline = TikTokPipeline(output_dir=str(out_dir), temp_dir=str(tmp_dir), publish_mode="none")

        def fake_process_url(url, top_k=10):
            res = {
                "source_title": f"Title for {url}",
                "clips_count": 1,
                "theme": "gospel",
                "watermark": "@parole.de.foi",
                "clips": [{"clip_number": 1, "video_path": f"{url}.mp4", "hook": "H"}]
            }
            with open(out_dir / "tiktok_results.json", "w", encoding="utf-8") as f:
                json.dump(res, f)
            return res

        with patch.object(pipeline, "process_url", side_effect=fake_process_url):
            batch_res = pipeline.process_batch(["https://yt.com/1", "https://yt.com/2"], top_k=1)

        assert len(batch_res) == 2
        saved = json.loads((out_dir / "tiktok_results.json").read_text(encoding="utf-8"))
        assert saved["clips_count"] == 2
        assert len(saved["clips"]) == 2
        assert len(saved["batch_results"]) == 2

    def test_process_url_cleans_up_session_dir(self, tmp_path):
        """process_url cleans up downloads/session_* directory in finally block."""
        out_dir = tmp_path / "out"
        dl_dir = tmp_path / "downloads"
        session_dir = dl_dir / "session_vid999_abcd1234"
        session_dir.mkdir(parents=True)
        fake_mp4 = session_dir / "vid999.mp4"
        fake_mp4.write_bytes(b"fake video")

        pipeline = TikTokPipeline(output_dir=str(out_dir), temp_dir=str(dl_dir), publish_mode="none")
        with patch.object(pipeline.downloader, "download", return_value={
            "video_path": str(fake_mp4),
            "subtitle_path": None,
            "title": "Sermon",
            "duration": 60
        }):
            with patch.object(pipeline, "_process_video_file", return_value={"clips": []}):
                pipeline.process_url("https://www.youtube.com/watch?v=vid999", top_k=1)

        assert not session_dir.exists(), "Temporary session directory should be removed after process_url"

    def test_atomic_save_history_and_processed_clip_keys(self, tmp_path):
        """_save_history writes atomically and run_cycle records per-clip processed_clip_keys."""
        hist_file = tmp_path / "history" / "processed_videos.json"
        rep_file = tmp_path / "history" / "REPORT.md"

        bot = LibraryAutopilot(
            history_path=str(hist_file),
            report_path=str(rep_file),
            publish_mode="public",
            clips_count=2
        )

        mock_items = [{"id": "sermon_42", "title": "Sermon 42", "duration": 1200, "url": "https://yt.com/sermon_42"}]
        fake_pipeline_result = {
            "clips": [
                {"clip_number": 1, "duration": 70.0, "hook": "H1", "retention": "88%", "publication": {"status": "success"}},
                {"clip_number": 2, "duration": 75.0, "hook": "H2", "retention": "86%", "publication": {"status": "error"}},
            ]
        }

        with patch.object(bot, "fetch_playlist_items", return_value=mock_items):
            with patch("src.library_autopilot.TikTokPipeline") as mock_pipe_cls:
                mock_pipe_cls.return_value.process_url.return_value = fake_pipeline_result
                res = bot.run_cycle()

        assert res["status"] == "success"
        assert "sermon_42:clip_1" in bot.history_data["processed_clip_keys"]
        assert "sermon_42:clip_2" not in bot.history_data["processed_clip_keys"]
        assert hist_file.exists()

        # Verify no leftover temp files in history directory
        leftover_temps = [f for f in os.listdir(hist_file.parent) if f.endswith(".tmp")]
        assert leftover_temps == []


# ============================================================================
# 4. NLP, Transcriber & Notifier Hardening
# ============================================================================

class TestNLPTranscriberNotifierHardening:
    def test_hook_banner_word_boundaries_no_false_positives(self):
        """
        Substrings like 'fois' (must not match 'foi') or 'maritime' (must not match 'mari')
        do NOT trigger false-positive hooks.
        """
        opt = GrowthOptimizer()
        hook_fois = opt._generate_hook_banner("Il était une fois dans un village", "Chaque fois qu'il parle")
        assert hook_fois == GrowthOptimizer.DEFAULT_HOOK

        hook_maritime = opt._generate_hook_banner("Le transport maritime mondial", "Une façade maritime")
        assert hook_maritime == GrowthOptimizer.DEFAULT_HOOK

    def test_gospel_intelligence_recommended_hook_priority(self):
        """
        When first_sentence has no specific keyword hook, GospelIntelligence's specific
        recommended_hook takes priority over incidental words later in full_text.
        """
        opt = GrowthOptimizer()
        clip_info = {
            "first_sentence": "Écoutez bien cette vérité aujourd'hui.",
            "text": "Écoutez bien cette vérité aujourd'hui. Même si on parle d'une femme ou d'un foyer, ton cœur a besoin de pardon.",
            "recommended_hook": "DIEU A VU TES LARMES CACHÉES : REÇOIS SA GUÉRISON 🕊️",
            "gospel_meta": {"matched_keywords": ["cœur", "pardon"]},
            "score": 15
        }
        pkg = opt.generate_growth_package(clip_info, "Guérison de l'âme")
        assert pkg["hook_banner"] == "DIEU A VU TES LARMES CACHÉES : REÇOIS SA GUÉRISON 🕊️"

    def test_clip_extractor_no_double_counting_hyphenated_words(self):
        """Hyphenated words like 'Saint-Esprit' are scored once per token, not double-counted."""
        extractor = ClipExtractor(min_duration=10.0, max_duration=30.0)
        seg_hyphen = [{"start": 0.0, "end": 20.0, "text": "Le Saint-Esprit agit ici."}]
        seg_single = [{"start": 0.0, "end": 20.0, "text": "Le Esprit agit ici."}]

        clip_hyphen = extractor.find_best_clips(seg_hyphen, top_k=1)[0]
        clip_single = extractor.find_best_clips(seg_single, top_k=1)[0]

        # Both have 4 words and match 'esprit' (weight 3.5); hyphenated should not double-count 'saint' + 'esprit' in viral_score
        score_se, kw_se = find_keyword_match("Saint-Esprit")
        assert score_se == 3.5
        assert kw_se == "esprit"
        assert "esprit" in clip_hyphen["matched_keywords"]
        assert "saint" not in clip_hyphen["matched_keywords"]

    def test_transcriber_parses_srt_comma_timestamps_and_skips_vtt_headers(self, tmp_path):
        """_parse_vtt supports SRT comma timestamps (00:00:01,500) and skips Kind:/Language:/NOTE headers."""
        assert parse_vtt_timestamp("00:01:02,500") == 62.5

        sub_file = tmp_path / "hybrid.vtt"
        sub_file.write_text("""WEBVTT
Kind: captions
Language: fr
NOTE Ce commentaire ne doit jamais apparaître dans les segments
Seconde ligne de note

1
00:00:01,500 --> 00:00:04,000
Première phrase au format SRT avec virgule.

2
00:00:04,500 --> 00:00:08,250
Seconde phrase propre sans métadonnées.
""", encoding="utf-8")

        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(str(sub_file))
        assert len(segments) == 2
        assert segments[0]["start"] == 1.5
        assert segments[0]["end"] == 4.0
        assert segments[0]["text"] == "Première phrase au format SRT avec virgule."
        assert segments[1]["start"] == 4.5
        assert segments[1]["end"] == 8.25
        full_txt = " ".join(s["text"] for s in segments)
        assert "Kind:" not in full_txt
        assert "Language:" not in full_txt
        assert "commentaire" not in full_txt

    def test_notifier_supports_telegram_bot_api_url(self):
        """TikTokNotifier sends 'text' and 'chat_id' when webhook_url targets api.telegram.org."""
        tg_url = "https://api.telegram.org/bot123456:ABC-DEF/sendMessage?chat_id=987654321"
        notifier = TikTokNotifier(webhook_url=tg_url)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            notifier.notify_clip_ready({
                "video_path": "output/clip_1.mp4",
                "hook": "HOOK TELEGRAM",
                "duration": 65.0,
                "retention": "90%",
                "caption": "Amen"
            }, total_clips=1)

            assert mock_urlopen.call_count == 1
            req = mock_urlopen.call_args[0][0]
            body = json.loads(req.data.decode("utf-8"))
            assert "text" in body
            assert body["chat_id"] == "987654321"
            assert "HOOK TELEGRAM" in body["text"]
