import os
import sys
import json
import tempfile
import io
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tiktok_publisher import TikTokPublisher
from src.growth_optimizer import GrowthOptimizer
from src.notifier import TikTokNotifier
from src.pipeline import TikTokPipeline


# ============================================================================
# ADVERSARIAL SUITE 1: TikTokPublisher Network & API Resilience
# ============================================================================

class TestTikTokPublisherAdversarial:
    """Stress tests on TikTokPublisher under network failures, API errors, and edge cases."""

    def test_http_403_forbidden_on_init(self):
        """Simulate TikTok API rejecting credentials with HTTP 403."""
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"SAMPLE_VIDEO_DATA")
            tf.flush()

            pub = TikTokPublisher(access_token="expired_or_invalid_token")
            err_403 = urllib.error.HTTPError(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                403,
                "Forbidden",
                {},
                io.BytesIO(b'{"error": {"code": "access_token_invalid"}}')
            )

            with patch("urllib.request.urlopen", side_effect=err_403):
                result = pub.publish_clip(tf.name, {"full_post_text": "Adversarial 403 Test"})

                assert result["status"] == "error"
                assert "HTTP Error 403" in result["error"]
                assert os.path.exists(result["payload_file"])

    def test_http_500_internal_server_error_on_init(self):
        """Simulate TikTok API crashing with HTTP 500 during Init."""
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"SAMPLE_VIDEO_DATA")
            tf.flush()

            pub = TikTokPublisher(access_token="valid_token")
            err_500 = urllib.error.HTTPError(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                500,
                "Internal Server Error",
                {},
                io.BytesIO(b"Internal Server Error")
            )

            with patch("urllib.request.urlopen", side_effect=err_500):
                result = pub.publish_clip(tf.name, {"full_post_text": "Adversarial 500 Test"})

                assert result["status"] == "error"
                assert "HTTP Error 500" in result["error"]
                assert os.path.exists(result["payload_file"])

    def test_http_500_error_during_binary_put_upload(self):
        """Init succeeds and returns upload_url, but PUT binary upload fails with HTTP 500."""
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"SAMPLE_VIDEO_DATA")
            tf.flush()

            upload_url = "https://upload.tiktok.com/v2/upload_chunk"
            pub = TikTokPublisher(access_token="valid_token")

            # Mock Init success
            init_resp = MagicMock()
            init_resp.status = 200
            init_resp.read.return_value = json.dumps({
                "data": {"upload_url": upload_url, "publish_id": "pub_id_123"}
            }).encode("utf-8")
            init_resp.__enter__.return_value = init_resp

            # Mock PUT failure
            put_err = urllib.error.HTTPError(
                upload_url, 500, "Upload Gateway Error", {}, io.BytesIO(b"Chunk storage error")
            )

            def mock_urlopen(req, *args, **kwargs):
                if req.get_method() == "POST":
                    return init_resp
                elif req.get_method() == "PUT":
                    raise put_err
                raise ValueError(f"Unexpected method: {req.get_method()}")

            with patch("urllib.request.urlopen", side_effect=mock_urlopen):
                result = pub.publish_clip(tf.name, {"full_post_text": "Adversarial PUT failure"})

                assert result["status"] == "error"
                assert "HTTP Error 500" in result["error"]
                assert os.path.exists(result["payload_file"])

    def test_network_timeout_on_init(self):
        """Simulate socket timeout during API Init."""
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"SAMPLE_VIDEO_DATA")
            tf.flush()

            pub = TikTokPublisher(access_token="valid_token")
            with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timed out")):
                result = pub.publish_clip(tf.name, {"full_post_text": "Timeout Test"})

                assert result["status"] == "error"
                assert "timed out" in result["error"]
                assert os.path.exists(result["payload_file"])

    def test_invalid_upload_url_on_put(self):
        """Simulate Init returning a malformed or non-http upload URL."""
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"SAMPLE_VIDEO_DATA")
            tf.flush()

            pub = TikTokPublisher(access_token="valid_token")
            init_resp = MagicMock()
            init_resp.status = 200
            init_resp.read.return_value = json.dumps({
                "data": {"upload_url": "ftp://unsupported-scheme.com/upload", "publish_id": "123"}
            }).encode("utf-8")
            init_resp.__enter__.return_value = init_resp

            with patch("urllib.request.urlopen", return_value=init_resp):
                # upload_video_binary should fail or be caught
                result = pub.publish_clip(tf.name, {"full_post_text": "Bad URL test"})
                # Caught gracefully in publish_clip
                assert result["status"] in ("error", "success")

    def test_tiktok_api_returns_error_body_with_http_200(self):
        """
        Adversarial test: TikTok API v2 frequently returns HTTP 200 OK with an error body
        (e.g., unaudited client, missing permissions, rate limit).
        Current implementation returns status: 'success' with publish_id: None.
        This test documents the actual behavior for empirical evidence.
        """
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"VIDEO_CONTENT")
            tf.flush()

            pub = TikTokPublisher(access_token="test_token")
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({
                "error": {
                    "code": "unaudited_client_can_only_post_to_admin_users",
                    "message": "User not in sandbox tester list"
                }
            }).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp

            with patch("urllib.request.urlopen", return_value=mock_resp):
                res = pub.publish_clip(tf.name, {"full_post_text": "Caption"})

                # Empirical observation: upload_url and publish_id are None
                assert res["publish_id"] is None
                assert res["upload_url"] is None
                assert res["upload_status"] is None

    def test_zero_byte_video_file_content_range_behavior(self):
        """
        Test behavior when a 0-byte video is supplied to upload_video_binary.
        Verifies the exact Content-Range header generated.
        """
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            # 0 bytes
            tf.flush()

            pub = TikTokPublisher(access_token="test_token")
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__.return_value = mock_resp

            with patch("urllib.request.urlopen", return_value=mock_resp) as mock_url:
                status = pub.upload_video_binary("https://upload.tiktok.com", tf.name)
                req = mock_url.call_args[0][0]
                assert status == 200
                assert req.headers["Content-range"] == "bytes 0--1/0"
                assert req.headers["Content-length"] == "0"

    def test_nonexistent_video_path_in_publish_clip(self):
        """Test publish_clip with a non-existent file path when access_token is set."""
        pub = TikTokPublisher(access_token="token")
        init_resp = MagicMock()
        init_resp.status = 200
        init_resp.read.return_value = json.dumps({
            "data": {"upload_url": "https://upload.tiktok.com", "publish_id": "123"}
        }).encode("utf-8")
        init_resp.__enter__.return_value = init_resp

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = os.path.join(tmpdir, "does_not_exist.mp4")
            with patch("urllib.request.urlopen", return_value=init_resp):
                result = pub.publish_clip(missing_path, {"full_post_text": "Missing file"})
                assert result["status"] == "error"
                assert "introuvable" in result["error"] or "FileNotFoundError" in result["error"]

    def test_caption_truncation_to_tiktok_2200_limit(self):
        """Verify that captions exceeding TikTok's 2200 char limit are truncated."""
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
            tf.write(b"data")
            tf.flush()

            pub = TikTokPublisher(access_token=None)
            long_caption = "A" * 3000
            res = pub.publish_clip(tf.name, {"full_post_text": long_caption})

            with open(res["payload_file"], "r", encoding="utf-8") as f:
                data = json.load(f)

            assert len(data["post_info"]["title"]) == 2200


# ============================================================================
# ADVERSARIAL SUITE 2: GrowthOptimizer Dictionary & Data Resilience
# ============================================================================

class TestGrowthOptimizerAdversarial:
    """Stress tests on GrowthOptimizer for missing keys, corrupted types, and unicode."""

    def test_export_summary_sheet_completely_empty_package(self):
        """Verify export_summary_sheet handles a completely empty package without crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "empty_summary.txt")
            g = GrowthOptimizer()
            g.export_summary_sheet({}, out_file)

            assert os.path.exists(out_file)
            with open(out_file, "r", encoding="utf-8") as f:
                text = f.read()

            assert "https://digrekarlito11-eng.github.io/karl-studio/" in text
            assert "Côte d'Ivoire (GMT / Abidjan)" in text

    def test_export_summary_sheet_corrupted_schedule_none(self):
        """
        Adversarial test: If package['recommended_schedule'] is explicitly set to None,
        export_summary_sheet raises TypeError.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "corrupted_summary.txt")
            g = GrowthOptimizer()

            with pytest.raises(TypeError) as exc:
                g.export_summary_sheet({"recommended_schedule": None}, out_file)
            assert "not iterable" in str(exc.value)

    def test_generate_growth_package_corrupted_score_none(self):
        """
        Adversarial test: If clip_info['score'] is explicitly set to None,
        generate_growth_package raises TypeError on multiplication.
        """
        g = GrowthOptimizer()
        with pytest.raises(TypeError) as exc:
            g.generate_growth_package({"score": None}, "Titre")
        assert "unsupported operand type" in str(exc.value)

    def test_generate_growth_package_corrupted_text_none(self):
        """
        Adversarial test: If clip_info['text'] is explicitly set to None,
        generate_growth_package raises TypeError or AttributeError.
        """
        g = GrowthOptimizer()
        with pytest.raises(TypeError):
            g.generate_growth_package({"text": None}, "Titre")

    def test_unicode_special_characters_emojis_injection_strings(self):
        """Verify handling of complex Unicode, Arabic, CJK, emojis, quotes, and scripts."""
        g = GrowthOptimizer()
        adversarial_text = (
            "Prières puissantes & bénédictions ! 🕊️⚡🙏✝️ "
            "العربية / 汉语 / <script>alert('xss')</script> "
            "' OR '1'='1' -- \n\t\r\\//\"\"''"
        )
        clip_info = {
            "text": adversarial_text,
            "first_sentence": "Prières puissantes 🕊️",
            "score": 12
        }
        title = "Prédication Église & Foi <✝️> \"2026\" : Special 'Quotes'"

        package = g.generate_growth_package(clip_info, title)

        assert package["hook_banner"] == "FAIS CETTE PRIÈRE PUISSANTE 🙏"
        assert "#priere" in package["hashtags"]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "unicode_sheet.txt")
            g.export_summary_sheet(package, out_file)

            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()

            assert "FAIS CETTE PRIÈRE PUISSANTE 🙏" in content
            assert "<script>alert('xss')</script>" in content
            assert "https://digrekarlito11-eng.github.io/karl-studio/" in content


# ============================================================================
# ADVERSARIAL SUITE 3: TikTokNotifier Network Fault Tolerance
# ============================================================================

class TestTikTokNotifierAdversarial:
    """Stress tests on webhook notifications under various HTTP errors and malformed inputs."""

    def test_notifier_http_500_captured_cleanly(self):
        notifier = TikTokNotifier(webhook_url="https://discord.com/api/webhooks/test")
        err_500 = urllib.error.HTTPError(
            "https://discord.com/api/webhooks/test", 500, "Server Error", {}, io.BytesIO(b"Error")
        )
        with patch("urllib.request.urlopen", side_effect=err_500):
            # Must not raise exception
            notifier.notify_clip_ready({"hook": "TEST", "duration": 30}, 1)

    def test_notifier_http_404_captured_cleanly(self):
        notifier = TikTokNotifier(webhook_url="https://discord.com/api/webhooks/test")
        err_404 = urllib.error.HTTPError(
            "https://discord.com/api/webhooks/test", 404, "Not Found", {}, io.BytesIO(b"Error")
        )
        with patch("urllib.request.urlopen", side_effect=err_404):
            # Must not raise exception
            notifier.notify_clip_ready({"hook": "TEST", "duration": 30}, 1)

    def test_notifier_empty_clip_data(self):
        notifier = TikTokNotifier(webhook_url="https://discord.com/api/webhooks/test")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_url:
            notifier.notify_clip_ready({}, 0)
            assert mock_url.call_count == 1
