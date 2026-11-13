"""
tests/test_e2e_pipeline.py - End-to-End and Cross-Feature Integration Tests.
Covers:
- Tier 3: Cross-Feature Interactions:
  - Media-Bot ↔ Growth-Bot contract data flow.
  - Theme consistency between ASS subtitle styles and FFmpeg progress bar.
  - Watermark placement in TikTok Safe Zone.
  - Pipeline ↔ TikTokPublisher API v2 draft payload contract.
  - DevOps-Bot notification formatting.
- Tier 4: Real-World Preaching Application Scenarios:
  - Full autonomous preaching pipeline execution with synthetic video & WebVTT.
  - Verification of all 4 generated deliverables:
    1. MP4 1080x1920 (9:16) vertical video.
    2. Summary sheet (FICHE_TIKTOK_*.txt) for Karl with hook, AMEN CTA, Abidjan GMT slots.
    3. TikTok API v2 draft payload JSON (*_tiktok_payload.json).
    4. Execution manifest (tiktok_results.json).
  - main.py --demo end-to-end workflow verification.
"""

import os
import json
import sys
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from src.pipeline import TikTokPipeline
from src.clip_extractor import ClipExtractor
from src.growth_optimizer import GrowthOptimizer
from src.themes import get_theme
from src.video_formatter import VideoFormatter
from src.tiktok_publisher import TikTokPublisher
from src.notifier import TikTokNotifier
import main

# ============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS
# ============================================================================

class TestCrossFeatureInteractions:
    """Verifies that individual bots integrate according to interface contracts."""

    def test_media_bot_to_growth_bot_contract(self, sample_preaching_segments):
        """
        ClipExtractor output dictionary feeds directly into GrowthOptimizer
        without data reformatting or missing key exceptions.
        """
        extractor = ClipExtractor(min_duration=25.0, max_duration=58.0)
        clips = extractor.find_best_clips(sample_preaching_segments, top_k=1)
        assert len(clips) >= 1
        clip = clips[0]

        growth = GrowthOptimizer()
        package = growth.generate_growth_package(clip, "Culte Prophétique")

        # Contract guarantees
        assert "hook_banner" in package
        assert "caption" in package
        assert "hashtags" in package
        assert "full_post_text" in package
        assert "recommended_schedule" in package
        assert "location_focus" in package
        assert "karl_studio_link" in package

        # Semantic alignment: clip starts with prophetic declaration -> prophetic hook
        assert package["hook_banner"] == "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️"

    def test_theme_color_consistency_ass_and_progress_bar(self):
        """
        Verifies color harmony for 'gospel' theme:
        ASS Hook color and subtitle highlight match progress bar gold.
        """
        theme = get_theme("gospel")
        formatter = VideoFormatter()

        # ASS BGR format &H0000D7FF& corresponds to RGB #FFD700
        assert theme["hook_color"] == "&H0000D7FF&"
        assert theme["sub_highlight"] == "&H0000D7FF&"
        assert theme["progress_color"] == "0xFFD700"

    def test_watermark_in_safe_zone(self, sample_preaching_segments, tmp_path):
        """
        Watermark is placed in the top-left Safe Zone (MarginL=45, MarginV=210)
        to prevent occlusion by TikTok UI interaction elements.
        """
        formatter = VideoFormatter(output_dir=str(tmp_path))
        ass_path = tmp_path / "safe_zone.ass"
        formatter.create_ass_subtitles(
            segments=sample_preaching_segments[:2],
            hook_title="TEST HOOK",
            ass_path=str(ass_path),
            clip_start=0.0,
            watermark="@parole.de.foi"
        )

        content = ass_path.read_text(encoding="utf-8")
        assert "Style: WatermarkBadge" in content
        # Alignment 7 is top-left in ASS format, with MarginL=45 and MarginV=210
        assert ",7,45,45,210,1" in content
        assert "WatermarkBadge,,0,0,0,,@parole.de.foi" in content

    def test_pipeline_to_tiktok_publisher_payload_contract(self, tmp_path):
        """
        TikTokPublisher creates standard API v2 draft payload matching TikTok specs.
        """
        dummy_video = tmp_path / "test_clip.mp4"
        dummy_video.write_bytes(b"dummy mp4 binary data of test size")

        growth_package = {
            "hook_banner": "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️",
            "full_post_text": "📖 Parole du jour\n\n#chretien #cotedivoire #abidjan",
            "estimated_retention": "88%"
        }

        publisher = TikTokPublisher()
        result = publisher.publish_clip(
            video_path=str(dummy_video),
            growth_package=growth_package,
            privacy_level="SELF_ONLY"
        )

        assert result["status"] == "ready_to_publish"
        payload_file = result["payload_file"]
        assert os.path.exists(payload_file)

        with open(payload_file, "r", encoding="utf-8") as f:
            payload = json.load(f)

        assert payload["post_info"]["title"] == growth_package["full_post_text"]
        assert payload["post_info"]["privacy_level"] == "SELF_ONLY"
        assert payload["post_info"]["video_cover_timestamp_ms"] == 1500
        assert payload["source_info"]["source"] == "FILE_UPLOAD"
        assert payload["source_info"]["video_size"] == len(b"dummy mp4 binary data of test size")

    def test_notifier_formatting_contract(self, capsys):
        """TikTokNotifier formats alert with hook, duration, and retention."""
        notifier = TikTokNotifier()
        clip_data = {
            "hook": "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️",
            "duration": 34.5,
            "retention": "88%",
            "video_path": "output/tiktok_Pasteur_clip_1_0s.mp4",
            "caption": "Reçois cette parole"
        }
        notifier.notify_clip_ready(clip_data, total_clips=1)

        captured = capsys.readouterr().out
        assert "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️" in captured
        assert "34.5s" in captured
        assert "tiktok_Pasteur_clip_1_0s.mp4" in captured


# ============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (Preaching Workflow for Karl)
# ============================================================================

class TestRealWorldPreachingWorkflow:
    """
    End-to-end integration tests simulating Karl's autonomous experience from Abidjan:
    From raw preaching video & subtitles to complete verified TikTok deliverables.
    """

    def test_e2e_synthetic_preaching_pipeline_execution(
        self,
        synthetic_preaching_video,
        sample_vtt_file,
        test_output_dir,
        test_temp_dir
    ):
        """
        Full A-to-Z execution of TikTokPipeline:
        1. Ingests source video and Christian preaching WebVTT subtitles.
        2. Detects best clip segment.
        3. Generates Growth-Bot strategic package (Gospel hooks, AMEN CTA, Abidjan GMT).
        4. Renders vertical 9:16 MP4 (1080x1920) with blurred background & golden progress bar.
        5. Generates summary sheet for Karl.
        6. Prepares TikTok API v2 draft payload.
        7. Writes global execution report.
        """
        pipeline = TikTokPipeline(
            output_dir=test_output_dir,
            temp_dir=test_temp_dir,
            theme_name="gospel",
            watermark="@parole.de.foi",
            with_progress_bar=True,
            publish_mode="draft"
        )

        results = pipeline._process_video_file(
            video_path=synthetic_preaching_video,
            video_title="Pasteur Marcello Tunasi - Prédication Céleste",
            subtitle_path=sample_vtt_file,
            top_k=1
        )

        # 1. Pipeline result manifest
        assert results["source_title"] == "Pasteur Marcello Tunasi - Prédication Céleste"
        assert results["clips_count"] == 1
        assert results["theme"] == "gospel"
        assert results["watermark"] == "@parole.de.foi"
        assert len(results["clips"]) == 1

        clip_info = results["clips"][0]
        assert clip_info["hook"] == "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️"
        assert "#cotedivoire" in clip_info["hashtags"]
        assert "#abidjan" in clip_info["hashtags"]

        # 2. Output MP4 file validation
        final_video_path = clip_info["video_path"]
        assert os.path.exists(final_video_path)
        assert os.path.getsize(final_video_path) > 1000

        # Validate resolution via ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            final_video_path
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        w, h = [int(v.strip()) for v in res.stdout.strip().split(",")]
        assert w == 1080
        assert h == 1920

        # 3. Summary sheet validation for Karl
        sheet_path = clip_info["sheet_path"]
        assert os.path.exists(sheet_path)
        sheet_text = open(sheet_path, "r", encoding="utf-8").read()
        assert "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️" in sheet_text
        assert "Écris 'AMEN' en commentaire pour sceller cette bénédiction 👇" in sheet_text
        assert "Côte d'Ivoire (GMT / Abidjan)" in sheet_text
        assert "05h30 - 06h45 GMT" in sheet_text
        assert "https://digrekarlito11-eng.github.io/karl-studio/" in sheet_text

        # 4. TikTok draft payload validation
        payload_path = final_video_path.rsplit(".", 1)[0] + "_tiktok_payload.json"
        assert os.path.exists(payload_path)
        with open(payload_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        assert payload["post_info"]["privacy_level"] == "SELF_ONLY"
        assert payload["source_info"]["source"] == "FILE_UPLOAD"

        # 5. Global results report validation
        global_summary = os.path.join(test_output_dir, "tiktok_results.json")
        assert os.path.exists(global_summary)

    def test_run_synthetic_demo_function_e2e(self, test_output_dir):
        """
        Directly executes main.run_synthetic_demo() in an isolated output dir.
        Verifies that the previously broken KeyError: 'karl_studio_link' is resolved
        and demo succeeds end-to-end.
        """
        result = main.run_synthetic_demo(
            output_dir=test_output_dir,
            theme="gospel",
            watermark="@karlstudio"
        )
        assert result is not None
        assert result["clips_count"] >= 1
        assert os.path.exists(os.path.join(test_output_dir, "tiktok_results.json"))

    def test_main_cli_demo_subprocess(self, test_output_dir):
        """
        Executes python main.py --demo via subprocess and verifies clean exit 0.
        """
        python_bin = sys.executable
        cmd = [
            python_bin,
            "main.py",
            "--demo",
            "--output", test_output_dir,
            "--theme", "gospel",
            "--watermark", "@parole.de.foi"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Process failed with stderr:\n{res.stderr}"
        assert "Démonstration réussie avec succès !" in res.stdout
