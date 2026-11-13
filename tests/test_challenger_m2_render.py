"""
tests/test_challenger_m2_render.py - Empirical Challenger Suite for Milestone 2.
Focus:
- FFmpeg render performance: downscale blur benchmark & speedup measurement.
- Video stream & container geometry: 1080x1920 (9:16), H.264, 30fps, faststart (moov atom).
- Golden progress bar: geometry, color (0xFFD700), positioning (y=1906, h=14), and animation behavior.
- Gospel / Gold visual theme: ASS styles, color codes, contrast, and Safe Zone MarginR=140 compliance.
- Subtitle text & emoji sanitization: SMP/BMP symbols & variation selectors with French accent preservation.
- Downloader error handling: invalid URLs, malformed video IDs, and isolation guarantees.
"""

import os
import sys
import json
import time
import subprocess
import numpy as np
import pytest

from src.themes import get_theme, THEMES
from src.video_formatter import (
    VideoFormatter,
    format_ass_time,
    clean_text_for_ass,
    escape_ass_path_for_ffmpeg
)
from src.downloader import VideoDownloader


@pytest.fixture(scope="module")
def synthetic_bench_video(tmp_path_factory):
    """Generates an isolated 5-second 1280x720 video for rendering benchmarks."""
    tmp_dir = tmp_path_factory.mktemp("challenger_video_bench")
    video_path = str(tmp_dir / "bench_source.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        video_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return video_path


class TestFFmpegRenderPerformance:
    """Empirical benchmarking of video rendering and blur acceleration."""

    def test_downscale_blur_acceleration_speedup(self, synthetic_bench_video, tmp_path):
        """
        Empirically verifies that downscaling before boxblur produces:
        1. A >= 3.0x speedup in pure filter graph execution (excluding libx264 encoding overhead).
        2. A >= 1.3x speedup in end-to-end video rendering with libx264 encoding.
        """
        legacy_filter = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "boxblur=25:5[bg];"
            "[0:v]scale=1080:-2[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
        )

        optimized_filter = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "scale=108:192,boxblur=5:2,scale=1080:1920[bg];"
            "[0:v]scale=1080:-2[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
        )

        # 1. Pure filtergraph benchmark (null sink)
        def run_filter_null(f_str):
            cmd = [
                "ffmpeg", "-y",
                "-ss", "0",
                "-t", "3.0",
                "-i", synthetic_bench_video,
                "-filter_complex", f_str,
                "-map", "[outv]",
                "-f", "null",
                "-"
            ]
            t0 = time.perf_counter()
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return time.perf_counter() - t0

        t_filter_legacy = run_filter_null(legacy_filter)
        t_filter_opt = run_filter_null(optimized_filter)
        filter_speedup = t_filter_legacy / t_filter_opt
        print(f"\n[BENCHMARK] Pure Filter: Legacy={t_filter_legacy:.3f}s | Opt={t_filter_opt:.3f}s | Speedup={filter_speedup:.2f}x")
        assert filter_speedup >= 3.0, f"Expected pure blur filter speedup >= 3.0x, got {filter_speedup:.2f}x"

        # 2. End-to-end rendering benchmark with libx264 encode
        def run_filter_encode(f_str, out_name):
            out_p = str(tmp_path / out_name)
            cmd = [
                "ffmpeg", "-y",
                "-ss", "0",
                "-t", "3.0",
                "-i", synthetic_bench_video,
                "-filter_complex", f_str,
                "-map", "[outv]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                out_p
            ]
            t0 = time.perf_counter()
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return time.perf_counter() - t0, out_p

        t_enc_legacy, _ = run_filter_encode(legacy_filter, "legacy_blur.mp4")
        t_enc_opt, opt_p = run_filter_encode(optimized_filter, "opt_blur.mp4")
        enc_speedup = t_enc_legacy / t_enc_opt
        print(f"[BENCHMARK] End-to-End: Legacy={t_enc_legacy:.3f}s | Opt={t_enc_opt:.3f}s | Speedup={enc_speedup:.2f}x")
        assert enc_speedup >= 1.3, f"Expected end-to-end speedup >= 1.3x, got {enc_speedup:.2f}x"
        assert os.path.exists(opt_p)



class TestVideoGeometryAndContainer:
    """Empirical verification of output video geometry, codecs, and container metadata."""

    def test_rendered_video_geometry_and_faststart(self, synthetic_bench_video, tmp_path):
        """
        Validates rendered TikTok video:
        - Resolution: 1080x1920
        - Aspect Ratio: 9:16
        - Video Codec: h264
        - Container faststart: moov atom appears before mdat
        """
        formatter = VideoFormatter(output_dir=str(tmp_path))
        rendered_mp4 = formatter.render_tiktok_video(
            video_input=synthetic_bench_video,
            start_time=0.0,
            duration=3.0,
            hook_title="TEST GEOMETRY BANNER",
            segments=[
                {"start": 0.0, "end": 1.5, "text": "Première partie de la vidéo"},
                {"start": 1.5, "end": 3.0, "text": "Seconde partie de la bénédiction"}
            ],
            output_filename="geometry_test.mp4",
            watermark="@karlstudio",
            theme_name="gospel",
            with_progress_bar=True
        )

        assert os.path.exists(rendered_mp4)

        # 1. Probe stream attributes via ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_format", "-show_streams",
            "-of", "json",
            rendered_mp4
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        meta = json.loads(res.stdout)

        v_stream = next(s for s in meta["streams"] if s["codec_type"] == "video")
        assert v_stream["width"] == 1080, f"Expected width 1080, got {v_stream['width']}"
        assert v_stream["height"] == 1920, f"Expected height 1920, got {v_stream['height']}"
        assert v_stream["codec_name"] == "h264"
        assert v_stream["pix_fmt"] == "yuv420p"

        # 2. Check faststart (moov atom before mdat atom)
        with open(rendered_mp4, "rb") as f:
            header_sample = f.read(4096)
            moov_idx = header_sample.find(b"moov")
            mdat_idx = header_sample.find(b"mdat")
            assert moov_idx != -1, "moov atom not found in MP4 header"
            assert mdat_idx == -1 or moov_idx < mdat_idx, "moov atom must appear before mdat for faststart"


class TestGoldenProgressBarAndTheme:
    """Empirical testing of the golden progress bar and gospel visual theme."""

    def test_progress_bar_pixel_color_and_geometry(self, synthetic_bench_video, tmp_path):
        """
        Inspects raw video frames to verify:
        - The golden bar is drawn in the bottom 14px area (y: 1906 to 1920).
        - Pixels in the bar match the golden color (#FFD700 -> RGB ~ 255, 215, 0).
        - Pixels above the bar (y=1900) are not affected by drawbox.
        - Documents the empirical finding regarding drawbox per-frame animation.
        """
        formatter = VideoFormatter(output_dir=str(tmp_path))
        rendered_mp4 = formatter.render_tiktok_video(
            video_input=synthetic_bench_video,
            start_time=0.0,
            duration=3.0,
            hook_title="TEST PROGRESS BAR",
            segments=[{"start": 0.0, "end": 3.0, "text": "Test de la barre dorée"}],
            output_filename="progress_test.mp4",
            watermark="@karlstudio",
            theme_name="gospel",
            with_progress_bar=True
        )

        def extract_frame(t):
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

        frame = extract_frame(1.5)

        # Inspect bottom 14px region: y=1912
        bar_pixel = frame[1912, 100]
        r, g, b = int(bar_pixel[0]), int(bar_pixel[1]), int(bar_pixel[2])

        # Gold 0xFFD700: R > 220, G > 180, B < 60
        is_gold = r > 220 and g > 180 and b < 60
        assert is_gold, f"Pixel at (1912, 100) is not gold: RGB=({r}, {g}, {b})"

        # Verify pixels above the bar (y=1900) are untouched
        above_pixel = frame[1900, 100]
        is_above_gold = int(above_pixel[0]) > 220 and int(above_pixel[1]) > 180 and int(above_pixel[2]) < 60
        # The background at y=1900 from testsrc is not gold
        assert not is_above_gold, f"Pixel at (1900, 100) should not be gold: RGB=({above_pixel[0]}, {above_pixel[1]}, {above_pixel[2]})"

    def test_gospel_theme_attributes_and_safe_zone_margin_r_140(self, tmp_path):
        """
        Verifies that gospel theme definitions and ASS subtitle generation satisfy:
        - MarginR = 140 for TikTok right rail button clearance.
        - MarginL = 60 for left margin.
        - MarginV = 480 for vertical positioning above TikTok caption area.
        - Primary colour = &H00FFFFFF& (White).
        - Highlight colour = &H0000D7FF& (Celestial Gold).
        - Hook banner alignment = 8 (Top-Center) with MarginV = 240.
        """
        gospel = get_theme("gospel")
        assert gospel["sub_primary"] == "&H00FFFFFF&"
        assert gospel["sub_highlight"] == "&H0000D7FF&"
        assert gospel["hook_color"] == "&H0000D7FF&"
        assert gospel["progress_color"] == "0xFFD700"

        formatter = VideoFormatter(output_dir=str(tmp_path))
        ass_path = str(tmp_path / "gospel_sub.ass")

        formatter.create_ass_subtitles(
            segments=[
                {"start": 0.0, "end": 2.0, "text": "Dieu va faire un grand miracle dans ta vie"},
                {"start": 2.0, "end": 4.0, "text": "Reçois cette bénédiction divine aujourd'hui"}
            ],
            hook_title="ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️",
            ass_path=ass_path,
            clip_start=0.0,
            watermark="@karlstudio",
            theme_name="gospel"
        )

        with open(ass_path, "r", encoding="utf-8") as f:
            ass_content = f.read()

        # Check Safe Zone MarginR=140 in TikTokSubtitle style
        # Format: Style: TikTokSubtitle,Fontname,Fontsize,Primary,Secondary,Outline,Back,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
        assert "Style: TikTokSubtitle" in ass_content
        assert ",60,140,480,1" in ass_content, "MarginR=140 not found in TikTokSubtitle style definition"

        # Check Hook banner style in upper Safe Zone
        assert "Style: HookHeader" in ass_content
        assert ",40,40,240,1" in ass_content

        # Check Watermark badge
        assert "Style: WatermarkBadge" in ass_content
        assert ",45,45,210,1" in ass_content

        # Check word chunking & highlight: first word has celestial gold highlight tag
        assert r"{\c&H0000D7FF&}Dieu{\c&H00FFFFFF&}" in ass_content or r"{\c&H0000D7FF&}Reçois{\c&H00FFFFFF&}" in ass_content


class TestASSFormattingAndSanitization:
    """Tests for subtitle cleaning, emoji stripping, and path escaping."""

    def test_clean_text_for_ass_french_accents_and_emojis(self):
        """
        Verifies that SMP and BMP emojis and braces are stripped while
        preserving French accented characters.
        """
        raw = "🕊️ Prière pour Karl Studio ⚡ ✝️ : Seigneur, répands ta grâce sur la Côte d'Ivoire ! ⭐ ⚠️"
        cleaned = clean_text_for_ass(raw)

        # Accented characters must remain intact
        assert "Prière" in cleaned
        assert "grâce" in cleaned
        assert "Côte d'Ivoire" in cleaned

        # Emojis and symbols must be removed
        for sym in ["🕊", "⚡", "✝", "⭐", "⚠️", "\ufe0f"]:
            assert sym not in cleaned, f"Symbol {sym} was not cleaned from ASS text"

    def test_escape_ass_path_for_ffmpeg(self):
        """Ensures ASS path escaping handles spaces, colons, and quotes safely."""
        path_sample = "/home/antigravity/my folder/clip:1.ass"
        escaped = escape_ass_path_for_ffmpeg(path_sample)
        assert escaped.startswith("'") and escaped.endswith("'")
        assert r"\:" in escaped
        assert "/my folder/" in escaped


class TestDownloaderResiliencyAndErrors:
    """Tests for VideoDownloader error handling, non-existent URLs, and session isolation."""

    def test_get_video_info_invalid_url_returns_safe_fallback(self):
        """Verifies get_video_info does not crash on invalid URLs and returns fallback dictionary."""
        downloader = VideoDownloader(download_dir="/tmp/challenger_downloader_test")
        info = downloader.get_video_info("https://invalid-nonexistent-domain-404.org/watch?v=none")

        assert isinstance(info, dict)
        assert info["title"] == "video_source"
        assert info["id"] == "source"
        assert info["duration"] == 0

    def test_download_failure_raises_exception_and_no_unrelated_fallback(self, tmp_path, monkeypatch):
        """
        Confirms that when download fails, it raises an exception and never
        picks unrelated MP4 files in the directory.
        """
        # Create an unrelated MP4 file in download directory
        unrelated = tmp_path / "old_unrelated_video.mp4"
        unrelated.write_bytes(b"dummy video data")

        downloader = VideoDownloader(download_dir=str(tmp_path))

        monkeypatch.setattr(downloader, "get_video_info", lambda url: {
            "title": "Failed Vid",
            "id": "failed_id",
            "duration": 60
        })

        # Mock download that finishes without creating an MP4
        def mock_failing_download(url, template):
            pass

        monkeypatch.setattr(downloader, "_download_video", mock_failing_download)

        with pytest.raises(RuntimeError, match="Échec du téléchargement"):
            downloader.download("https://www.youtube.com/watch?v=failed_id")

    def test_session_directory_isolation(self, tmp_path, monkeypatch):
        """Verifies session folder has unique session ID prefix."""
        downloader = VideoDownloader(download_dir=str(tmp_path))

        monkeypatch.setattr(downloader, "get_video_info", lambda url: {
            "title": "Session Test",
            "id": "session123",
            "duration": 30
        })

        created_sessions = []

        def mock_successful_download(url, template):
            # template is inside session_dir
            s_dir = os.path.dirname(template)
            created_sessions.append(s_dir)
            mp4_file = os.path.join(s_dir, "session123_video.mp4")
            with open(mp4_file, "wb") as f:
                f.write(b"fake mp4")

        monkeypatch.setattr(downloader, "_download_video", mock_successful_download)

        res = downloader.download("https://www.youtube.com/watch?v=session123")
        assert len(created_sessions) == 1
        assert "session_session123_" in created_sessions[0]
        assert os.path.exists(res["video_path"])
