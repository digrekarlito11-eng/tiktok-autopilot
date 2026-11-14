"""
tests/test_media_bot.py - Comprehensive tests for Media-Bot components.
Covers:
- Tier 1: Feature coverage (VideoDownloader, VideoTranscriber, ClipExtractor, Themes, VideoFormatter).
- Tier 2: Boundary & corner cases (empty segments, short clips, special characters, ASS escaping).
- Tier 3: Visual theme consistency & ASS style verification.
"""

import os
import sys
import re
import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from src.downloader import VideoDownloader
from src.transcriber import VideoTranscriber, parse_vtt_timestamp, clean_subtitle_text, deduplicate_rolling_text
from src.clip_extractor import ClipExtractor, VIRAL_KEYWORDS, normalize_french_word, stem_french_word, find_keyword_match
from src.themes import get_theme, THEMES
from src.video_formatter import VideoFormatter, format_ass_time, clean_text_for_ass, escape_ass_path_for_ffmpeg


# ============================================================================
# TIER 1: FEATURE COVERAGE — VideoDownloader Resiliency
# ============================================================================

class TestVideoDownloader:
    """Tests for yt-dlp invocation resilience, session isolation, and fallback prevention."""

    def test_get_video_info_invokes_sys_executable_yt_dlp(self, monkeypatch):
        """Ensures yt-dlp is executed via [sys.executable, '-m', 'yt_dlp', ...]."""
        downloader = VideoDownloader()
        captured_cmd = []

        def mock_run(cmd, capture_output=True, text=True, check=True):
            captured_cmd.extend(cmd)
            mock_res = MagicMock()
            mock_res.stdout = json.dumps({"title": "Test Video", "id": "test_id", "duration": 120})
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)
        info = downloader.get_video_info("https://www.youtube.com/watch?v=test_id")

        assert captured_cmd[0] == sys.executable
        assert captured_cmd[1:3] == ["-m", "yt_dlp"]
        assert "--dump-json" in captured_cmd
        assert info["title"] == "Test Video"
        assert info["id"] == "test_id"

    def test_download_video_invokes_sys_executable_yt_dlp(self, monkeypatch):
        """Ensures video download executes via [sys.executable, '-m', 'yt_dlp', ...]."""
        downloader = VideoDownloader()
        captured_cmd = []

        def mock_run(cmd, check=True):
            captured_cmd.extend(cmd)
            return MagicMock()

        monkeypatch.setattr(subprocess, "run", mock_run)
        downloader._download_video("https://www.youtube.com/watch?v=test_id", "dummy_template")

        assert captured_cmd[0] == sys.executable
        assert captured_cmd[1:3] == ["-m", "yt_dlp"]
        assert "--write-auto-subs" in captured_cmd

    def test_download_creates_isolated_session_dir_and_no_unrelated_fallback(self, tmp_path, monkeypatch):
        """
        Critical security test:
        If download fails to produce a video, it MUST NOT fallback to picking an
        unrelated MP4 in download_dir, and MUST raise RuntimeError.
        """
        # Place an unrelated MP4 file in the main download directory
        unrelated_file = tmp_path / "unrelated_previous_video.mp4"
        unrelated_file.write_bytes(b"dummy previous data")

        downloader = VideoDownloader(download_dir=str(tmp_path))

        monkeypatch.setattr(downloader, "get_video_info", lambda url: {
            "title": "New Video",
            "id": "new_video_id",
            "duration": 50
        })

        def mock_download_nothing(url, template):
            pass

        monkeypatch.setattr(downloader, "_download_video", mock_download_nothing)

        with pytest.raises(RuntimeError, match="Échec du téléchargement"):
            downloader.download("https://www.youtube.com/watch?v=new_video_id")

    def test_download_success_isolated_session(self, tmp_path, monkeypatch):
        """Verifies successful download returns files from the dedicated session directory."""
        downloader = VideoDownloader(download_dir=str(tmp_path))

        monkeypatch.setattr(downloader, "get_video_info", lambda url: {
            "title": "Prédication Puissante",
            "id": "vid123",
            "duration": 45
        })

        def mock_download_success(url, template):
            session_dir = os.path.dirname(template)
            video_file = os.path.join(session_dir, "vid123_Prédication.mp4")
            sub_file = os.path.join(session_dir, "vid123_Prédication.fr.vtt")
            with open(video_file, "wb") as f:
                f.write(b"video content")
            with open(sub_file, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n")

        monkeypatch.setattr(downloader, "_download_video", mock_download_success)

        res = downloader.download("https://www.youtube.com/watch?v=vid123")
        assert res["title"] == "Prédication Puissante"
        assert res["duration"] == 45
        assert res["video_path"].endswith(".mp4")
        assert os.path.exists(res["video_path"])
        assert "session_vid123_" in res["video_path"]
        assert res["subtitle_path"].endswith(".vtt")

    def test_download_video_falls_back_across_youtube_clients_and_cleans_partials(self, tmp_path, monkeypatch):
        """Falls back across YouTube strategies with subtitles preserved when primary client hits bot-check."""
        downloader = VideoDownloader(download_dir=str(tmp_path))
        session_dir = tmp_path / "session_yt_fallback"
        session_dir.mkdir()
        part_file = session_dir / "temp.mp4.part"
        part_file.write_bytes(b"partial")

        seen_cmds = []

        def mock_run(cmd, check=True):
            seen_cmds.append(list(cmd))
            # Fail the first attempt (tv,web_embedded), succeed on second (ipv4+default_ejs)
            if len(seen_cmds) == 1:
                raise subprocess.CalledProcessError(1, cmd)
            return MagicMock()

        monkeypatch.setattr(subprocess, "run", mock_run)
        output_tpl = str(session_dir / "vid_%(title).40s.%(ext)s")
        downloader._download_video("https://www.youtube.com/watch?v=test_id", output_tpl)

        assert len(seen_cmds) == 2
        assert "tv,web_embedded" in " ".join(seen_cmds[0])
        assert "--force-ipv4" in seen_cmds[1]
        assert "--write-auto-subs" in seen_cmds[1]
        assert not part_file.exists()

    def test_get_video_info_falls_back_across_youtube_clients(self, monkeypatch):
        """Falls back to secondary YouTube client strategies when tv,web_embedded metadata fetch fails."""
        downloader = VideoDownloader()
        calls = []

        def mock_run(cmd, capture_output=True, text=True, check=True):
            calls.append(list(cmd))
            if len(calls) < len(VideoDownloader.YOUTUBE_STRATEGIES):
                raise subprocess.CalledProcessError(1, cmd)
            mock_res = MagicMock()
            mock_res.stdout = json.dumps({"title": "Sermon Résilient", "id": "res_123", "duration": 600})
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)
        info = downloader.get_video_info("https://www.youtube.com/watch?v=res_123")

        assert len(calls) == len(VideoDownloader.YOUTUBE_STRATEGIES)
        assert "android_vr" in " ".join(calls[-1])
        assert info["id"] == "res_123"
        assert info["title"] == "Sermon Résilient"


# ============================================================================
# TIER 1: FEATURE COVERAGE — VideoTranscriber & VTT Parsing
# ============================================================================

class TestVideoTranscriber:
    """Tests for subtitle parsing, timestamps, cleanup, and rolling-window deduplication."""

    def test_parse_vtt_timestamp_formats(self):
        """Supports HH:MM:SS.mmm, MM:SS.mmm, and raw seconds."""
        assert parse_vtt_timestamp("01:02:03.456") == 3600 + 120 + 3.456
        assert parse_vtt_timestamp("02:15.500") == 135.5
        assert parse_vtt_timestamp("45.250") == 45.25

    def test_clean_subtitle_text_strips_tags_and_brackets(self):
        """Removes HTML tags, sound descriptions [Musique], and trims spaces."""
        raw = " <c.color>Dieu</c> va [Musique] agir avec <b>puissance</b> !  "
        cleaned = clean_subtitle_text(raw)
        assert cleaned == "Dieu va agir avec puissance !"

    def test_parse_vtt_file_success(self, sample_vtt_file):
        """Parses a complete WebVTT file into ordered segments with start, end, and text."""
        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(sample_vtt_file)
        assert len(segments) == 5
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 4.5
        assert "message prophétique" in segments[0]["text"]
        assert segments[-1]["end"] == 33.0
        assert "bénédiction divine" in segments[-1]["text"]

    def test_transcribe_prefers_subtitle_file_when_present(self, sample_vtt_file):
        """Uses fast native VTT file when provided without invoking Whisper."""
        transcriber = VideoTranscriber()
        segments = transcriber.transcribe(video_path="dummy.mp4", subtitle_path=sample_vtt_file)
        assert len(segments) == 5
        assert segments[0]["text"].startswith("Écoutez")

    def test_deduplicate_rolling_text_unit(self):
        """Direct unit test on deduplicate_rolling_text helper."""
        assert deduplicate_rolling_text("Dieu est amour", "Le Seigneur est bon") == "Le Seigneur est bon"
        prev = "Dieu va faire un miracle"
        curr = "Dieu va faire un miracle dans ta vie reçois"
        assert deduplicate_rolling_text(prev, curr) == "dans ta vie reçois"
        assert deduplicate_rolling_text("Dieu est fidèle", "Dieu est fidèle") == ""
        prev2 = "dans ta vie reçois"
        curr2 = "dans ta vie reçois cette bénédiction"
        assert deduplicate_rolling_text(prev2, curr2) == "cette bénédiction"

    def test_parse_vtt_rolling_window_deduplication(self, rolling_vtt_file):
        """
        Parses a YouTube auto-generated rolling WebVTT file and verifies that
        rolling-window caption duplication is completely eliminated.
        """
        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(rolling_vtt_file)

        assert len(segments) == 3
        assert segments[0]["text"] == "Dieu va faire un miracle"
        assert segments[1]["text"] == "dans ta vie reçois"
        assert segments[2]["text"] == "cette bénédiction aujourd'hui"

        combined = " ".join(s["text"] for s in segments)
        assert combined == "Dieu va faire un miracle dans ta vie reçois cette bénédiction aujourd'hui"
        assert combined.count("Dieu va faire un miracle") == 1
        assert combined.count("dans ta vie reçois") == 1

    def test_rolling_vtt_identical_cue_merging(self, tmp_path):
        """Identical consecutive cues merge timestamps instead of duplicating segments."""
        vtt = tmp_path / "identical_cues.vtt"
        vtt.write_text("""WEBVTT

00:00:01.000 --> 00:00:03.000
Gloire à Dieu

00:00:03.000 --> 00:00:05.000
Gloire à Dieu
""", encoding="utf-8")

        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(str(vtt))
        assert len(segments) == 1
        assert segments[0]["start"] == 1.0
        assert segments[0]["end"] == 5.0
        assert segments[0]["text"] == "Gloire à Dieu"


# ============================================================================
# TIER 1: FEATURE COVERAGE — ClipExtractor & French NLP
# ============================================================================

class TestClipExtractor:
    """Tests for viral scoring, French NLP (elisions, plurals), duration windowing, and highlight extraction."""

    def test_viral_keywords_weights(self):
        """Verifies high weights for core spiritual keywords."""
        assert VIRAL_KEYWORDS["dieu"] >= 3.0
        assert VIRAL_KEYWORDS["jésus"] >= 3.0
        assert VIRAL_KEYWORDS["miracle"] >= 4.0
        assert VIRAL_KEYWORDS["prophétie"] >= 4.0
        assert VIRAL_KEYWORDS["délivrance"] >= 4.0

    def test_spiritual_keywords_expansion(self):
        """Verifies expansion of VIRAL_KEYWORDS with all required spiritual terms."""
        spiritual_terms = [
            "miracle", "miracles",
            "priere", "prieres", "prière", "prières",
            "benediction", "benedictions", "bénédiction", "bénédictions",
            "eternel", "éternel",
            "onction", "onctions",
            "combat", "combats",
            "delivrance", "délivrance",
            "foi",
            "grace", "grâce"
        ]
        for term in spiritual_terms:
            assert term in VIRAL_KEYWORDS, f"Missing term: {term}"
            assert VIRAL_KEYWORDS[term] >= 3.0

    def test_french_nlp_normalization_elisions(self):
        """Strips leading l', d', c', qu' and keeps root alphabetic word."""
        assert normalize_french_word("l'onction") == "onction"
        assert normalize_french_word("d'onctions") == "onctions"
        assert normalize_french_word("c'est") == "est"
        assert normalize_french_word("qu'il") == "il"
        assert normalize_french_word("l’Éternel") == "éternel"

    def test_french_nlp_stemming_plurals(self):
        """Strips terminal s or x for regular French plurals."""
        assert stem_french_word("miracles") == "miracle"
        assert stem_french_word("combats") == "combat"
        assert stem_french_word("bénédictions") == "bénédiction"
        assert stem_french_word("prières") == "prière"
        assert stem_french_word("foi") == "foi"

    def test_find_keyword_match_elision_and_plurals(self):
        """Correctly matches scores for words with elision and plurals."""
        score1, kw1 = find_keyword_match("l'onction")
        assert score1 == 3.5
        assert kw1 == "onction"

        score2, kw2 = find_keyword_match("d'onctions")
        assert score2 == 3.5

        score3, kw3 = find_keyword_match("combats")
        assert score3 == 3.0

        score4, kw4 = find_keyword_match("miracles")
        assert score4 == 4.0

    def test_clip_extractor_french_nlp_scoring_with_elision_and_plurals(self):
        """Verifies that elided and plural words contribute to viral score and matched_keywords."""
        segments = [
            {
                "start": 0.0,
                "end": 30.0,
                "text": "Recevez l'onction divine pour surmonter tous les combats spirituels et voir des miracles."
            }
        ]
        extractor = ClipExtractor(min_duration=25.0, max_duration=35.0)
        clips = extractor.find_best_clips(segments, top_k=1)
        assert len(clips) == 1
        clip = clips[0]
        assert clip["score"] > 0
        assert "matched_keywords" in clip
        assert any("onction" in kw for kw in clip["matched_keywords"])
        assert any("combat" in kw for kw in clip["matched_keywords"])
        assert any("miracle" in kw for kw in clip["matched_keywords"])

    def test_clip_extractor_duration_bounds(self, sample_preaching_segments):
        """Extracted clip must respect min_duration (25s) and max_duration (58s)."""
        extractor = ClipExtractor(min_duration=25.0, max_duration=58.0)
        clips = extractor.find_best_clips(sample_preaching_segments, top_k=1)

        assert len(clips) == 1
        clip = clips[0]
        assert clip["duration"] >= 25.0
        assert clip["duration"] <= 58.0
        assert clip["score"] > 0
        assert "segments" in clip
        assert "first_sentence" in clip

    def test_clip_extractor_prefers_high_viral_density(self):
        """Clip with dense spiritual keywords scores higher than generic talk."""
        neutral_segments = [
            {"start": float(i * 5), "end": float((i + 1) * 5), "text": f"Information technique standard partie {i}."}
            for i in range(7)  # 35 seconds total
        ]
        spiritual_segments = [
            {"start": 0.0, "end": 10.0, "text": "Dieu va libérer un grand miracle et une délivrance divine."},
            {"start": 10.0, "end": 20.0, "text": "Jésus est le Seigneur de ta foi et ta victoire est assurée."},
            {"start": 20.0, "end": 30.0, "text": "Reçois cette prophétie et cette bénédiction puissante."}
        ]

        extractor = ClipExtractor(min_duration=25.0, max_duration=35.0)
        neutral_clips = extractor.find_best_clips(neutral_segments, top_k=1)
        spiritual_clips = extractor.find_best_clips(spiritual_segments, top_k=1)

        assert spiritual_clips[0]["score"] > neutral_clips[0]["score"]

    def test_clip_extractor_short_video_fallback(self):
        """When total video duration is shorter than min_duration, fallback produces full span."""
        short_segments = [
            {"start": 0.0, "end": 5.0, "text": "Courte prière du matin."},
            {"start": 5.0, "end": 12.0, "text": "Que la grâce soit avec toi."}
        ]
        extractor = ClipExtractor(min_duration=25.0, max_duration=58.0)
        clips = extractor.find_best_clips(short_segments, top_k=1)

        assert len(clips) == 1
        assert clips[0]["start"] == 0.0
        assert clips[0]["end"] == 12.0
        assert clips[0]["duration"] == 12.0
        assert clips[0]["score"] == 10.0

    def test_clip_extractor_empty_segments(self):
        """Empty segments input gracefully returns empty list."""
        extractor = ClipExtractor()
        assert extractor.find_best_clips([]) == []

    def test_clip_extractor_extract_highlights_alias(self, sample_preaching_segments):
        """extract_highlights is an alias for find_best_clips."""
        extractor = ClipExtractor()
        clips1 = extractor.find_best_clips(sample_preaching_segments, top_k=1)
        clips2 = extractor.extract_highlights(sample_preaching_segments, top_k=1)
        assert clips1 == clips2


# ============================================================================
# TIER 1: FEATURE COVERAGE — Themes & Visual Palette
# ============================================================================

class TestThemes:
    """Tests for graphic themes and Gospel color palette."""

    def test_all_defined_themes_exist(self):
        """All 4 standard themes must be properly declared."""
        for name in ["gospel", "gold", "neon", "minimal"]:
            theme = get_theme(name)
            assert "name" in theme
            assert "hook_color" in theme
            assert "hook_outline" in theme
            assert "sub_primary" in theme
            assert "sub_highlight" in theme
            assert "progress_color" in theme
            assert "font_name" in theme

    def test_gospel_theme_color_matching(self):
        """Gospel theme uses Celestial Gold for hook/highlight and matching progress bar."""
        gospel = get_theme("gospel")
        assert gospel["hook_color"] == "&H0000D7FF&"       # Celestial Gold in ASS BGR
        assert gospel["sub_highlight"] == "&H0000D7FF&"    # Highlight matches hook
        assert gospel["sub_primary"] == "&H00FFFFFF&"      # Pure white
        assert gospel["progress_color"] == "0xFFD700"      # Gold in FFmpeg hex

    def test_theme_fallback_to_gospel(self):
        """Unknown theme name gracefully defaults to gospel."""
        theme = get_theme("non_existent_theme")
        assert theme["name"] == THEMES["gospel"]["name"]


# ============================================================================
# TIER 1 & TIER 2: VideoFormatter (ASS Generation, Escaping & FFmpeg Rendering)
# ============================================================================

class TestVideoFormatter:
    """Tests for ASS subtitle formatting, Safe Zone layout, and FFmpeg execution."""

    def test_format_ass_time(self):
        """Accurately formats seconds to H:MM:SS.cs."""
        assert format_ass_time(0.0) == "0:00:00.00"
        assert format_ass_time(65.5) == "0:01:05.50"
        assert format_ass_time(3661.25) == "1:01:01.25"

    def test_clean_text_for_ass_with_bmp_emojis_and_selectors(self):
        """Strips SMP emojis, BMP emojis (⚡, ✝️, ⚠️, ⭐), and selector \ufe0f while preserving French accents."""
        dirty = "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️ {tag} 🙏 ⚡ ✝️ ⚠️ ⭐"
        clean = clean_text_for_ass(dirty)
        assert "🕊" not in clean
        assert "\ufe0f" not in clean
        assert "{" not in clean
        assert "}" not in clean
        assert "⚡" not in clean
        assert "✝" not in clean
        assert "⚠️" not in clean
        assert "⭐" not in clean
        assert clean == "ÉCOUTE CE MESSAGE PROPHÉTIQUE tag"

    def test_escape_ass_path_for_ffmpeg(self):
        """Safely escapes spaces, colons, and backslashes for FFmpeg filtergraph."""
        path_with_space = "/tmp/my dir/sub title.ass"
        escaped = escape_ass_path_for_ffmpeg(path_with_space)
        assert escaped == f"'{os.path.abspath(path_with_space)}'"

        path_with_colon = "/tmp/my:clip/sub.ass"
        escaped_colon = escape_ass_path_for_ffmpeg(path_with_colon)
        assert r"\:" in escaped_colon
        assert escaped_colon.startswith("'") and escaped_colon.endswith("'")

    def test_create_ass_subtitles_margin_r_140(self, sample_preaching_segments, tmp_path):
        """Verifies MarginR=140 in ASS header for TikTok Safe Zone."""
        formatter = VideoFormatter(output_dir=str(tmp_path))
        ass_path = tmp_path / "test_margin.ass"

        formatter.create_ass_subtitles(
            segments=sample_preaching_segments[:1],
            hook_title="TEST SAFE ZONE",
            ass_path=str(ass_path),
            clip_start=0.0
        )

        content = ass_path.read_text(encoding="utf-8")
        assert "Style: TikTokSubtitle" in content
        assert ",60,140,480,1" in content

    def test_create_ass_subtitles_structure(self, sample_preaching_segments, tmp_path):
        """Generates well-formed ASS script with styles, Hook banner, Watermark, and subtitle chunks."""
        formatter = VideoFormatter(output_dir=str(tmp_path))
        ass_path = tmp_path / "test.ass"

        formatter.create_ass_subtitles(
            segments=sample_preaching_segments,
            hook_title="ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️",
            ass_path=str(ass_path),
            clip_start=0.0,
            watermark="@parole.de.foi",
            theme_name="gospel"
        )

        assert ass_path.exists()
        content = ass_path.read_text(encoding="utf-8")

        # Check Script Info & 9:16 resolution
        assert "PlayResX: 1080" in content
        assert "PlayResY: 1920" in content

        # Check Styles
        assert "Style: HookHeader" in content
        assert "Style: TikTokSubtitle" in content
        assert "Style: WatermarkBadge" in content

        # Check Watermark dialogue in Safe Zone
        assert "@parole.de.foi" in content
        assert "WatermarkBadge" in content

        # Check Hook dialogue
        assert "HookHeader" in content

        # Check subtitle highlight tag
        assert r"{\c&H0000D7FF&}" in content

    def test_render_filtergraph_downscaled_blur_optimization(self, monkeypatch, tmp_path):
        """Verifies FFmpeg filtergraph uses downscaled blur optimization scale=108:192,boxblur=5:2,scale=1080:1920."""
        formatter = VideoFormatter(output_dir=str(tmp_path))
        captured_filter = []

        def mock_run(cmd, check=True):
            if "-filter_complex" in cmd:
                idx = cmd.index("-filter_complex")
                captured_filter.append(cmd[idx + 1])
            with open(cmd[-1], "wb") as f:
                f.write(b"mp4")
            return MagicMock()

        monkeypatch.setattr(subprocess, "run", mock_run)

        formatter.render_tiktok_video(
            video_input="dummy.mp4",
            start_time=0.0,
            duration=3.0,
            hook_title="TEST BLUR",
            segments=[],
            output_filename="test_opt.mp4",
            with_progress_bar=True
        )

        assert len(captured_filter) == 1
        fgraph = captured_filter[0]
        assert "scale=108:192,boxblur=5:2,scale=1080:1920" in fgraph

    def test_render_tiktok_video_synthetic(self, synthetic_preaching_video, sample_preaching_segments, tmp_path):
        """
        Renders a real short 9:16 MP4 video via FFmpeg to test filtergraph integrity:
        blurred background + foreground crop + ASS subtitles + animated golden progress bar.
        """
        formatter = VideoFormatter(output_dir=str(tmp_path))
        output_filename = "rendered_unit_test.mp4"

        # Clip of 3 seconds from the 5-second synthetic video
        final_mp4 = formatter.render_tiktok_video(
            video_input=synthetic_preaching_video,
            start_time=0.0,
            duration=3.0,
            hook_title="TEST HOOK BANNER",
            segments=sample_preaching_segments[:1],
            output_filename=output_filename,
            watermark="@karlstudio",
            theme_name="gospel",
            with_progress_bar=True
        )

        assert os.path.exists(final_mp4)
        assert os.path.getsize(final_mp4) > 1000

        # Probe the resulting video to verify 1080x1920 9:16 vertical resolution
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            final_mp4
        ]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        lines = probe_res.stdout.strip().split("\n")
        width, height = int(lines[0]), int(lines[1])
        assert width == 1080
        assert height == 1920

    def test_render_without_progress_bar(self, synthetic_preaching_video, sample_preaching_segments, tmp_path):
        """Renders without progress bar using copy filter instead of drawbox."""
        formatter = VideoFormatter(output_dir=str(tmp_path))
        final_mp4 = formatter.render_tiktok_video(
            video_input=synthetic_preaching_video,
            start_time=0.0,
            duration=2.0,
            hook_title="TEST NO BAR",
            segments=sample_preaching_segments[:1],
            output_filename="no_bar.mp4",
            watermark="@karlstudio",
            theme_name="minimal",
            with_progress_bar=False
        )
        assert os.path.exists(final_mp4)

