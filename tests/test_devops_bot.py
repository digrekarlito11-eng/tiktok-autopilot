import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import tempfile
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock
import pytest

from src.tiktok_publisher import TikTokPublisher
from src.growth_optimizer import GrowthOptimizer
from src.notifier import TikTokNotifier
import main


# =====================================================================
# Tests TikTokPublisher (Phase 1 Init + Phase 2 Binary PUT Upload + Offline)
# =====================================================================

def test_tiktok_publisher_offline_draft_payload():
    """Vérifie la génération propre du payload JSON en mode sans token (offline/draft)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_video = os.path.join(tmpdir, "clip_test.mp4")
        with open(fake_video, "wb") as f:
            f.write(b"\x00" * 2048)  # 2KB fake video

        growth_package = {
            "hook_banner": "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️",
            "full_post_text": "Voici un extrait puissant sur la foi chrétienne #chretien #abidjan",
            "estimated_retention": "85%"
        }

        # S'assurer qu'aucun token d'environnement ne pollue le test
        with patch.dict(os.environ, {}, clear=True):
            publisher = TikTokPublisher(access_token=None)
            result = publisher.publish_clip(
                video_path=fake_video,
                growth_package=growth_package,
                privacy_level="SELF_ONLY"
            )

        assert result["status"] == "ready_to_publish"
        assert result["method"] == "ready_package"
        assert result["privacy_level"] == "SELF_ONLY"

        payload_path = result["payload_file"]
        assert os.path.exists(payload_path)
        assert payload_path == os.path.join(tmpdir, "clip_test_tiktok_payload.json")

        with open(payload_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        assert payload["post_info"]["title"] == growth_package["full_post_text"]
        assert payload["post_info"]["privacy_level"] == "SELF_ONLY"
        assert payload["post_info"]["video_cover_timestamp_ms"] == 1500
        assert payload["source_info"]["source"] == "FILE_UPLOAD"
        assert payload["source_info"]["video_size"] == 2048
        assert payload["source_info"]["chunk_size"] == 2048
        assert payload["source_info"]["total_chunk_count"] == 1


def test_tiktok_publisher_upload_video_binary():
    """Vérifie que la méthode upload_video_binary envoie un HTTP PUT binaire avec les en-têtes corrects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_video = os.path.join(tmpdir, "sample.mp4")
        video_content = b"TEST_MP4_BINARY_PAYLOAD_CHUNK_DATA_1234567890"
        with open(fake_video, "wb") as f:
            f.write(video_content)

        file_size = len(video_content)
        upload_url = "https://open-upload.tiktokapis.com/video/?upload_token=xyz987"

        publisher = TikTokPublisher(access_token="dummy_token")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_response.read.return_value = b'{"code": 0, "message": "success"}'

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            status = publisher.upload_video_binary(upload_url, fake_video)

            assert status == 200
            assert mock_urlopen.call_count == 1

            req_called = mock_urlopen.call_args[0][0]
            assert isinstance(req_called, urllib.request.Request)
            assert req_called.full_url == upload_url
            assert req_called.get_method() == "PUT"
            assert req_called.data == video_content

            headers = {k.lower(): v for k, v in req_called.headers.items()}
            assert headers["content-type"] == "video/mp4"
            assert headers["content-range"] == f"bytes 0-{file_size - 1}/{file_size}"
            assert headers["content-length"] == str(file_size)


def test_tiktok_publisher_upload_video_binary_file_not_found():
    """Vérifie que upload_video_binary lève FileNotFoundError si le fichier n'existe pas."""
    publisher = TikTokPublisher(access_token="dummy_token")
    with pytest.raises(FileNotFoundError):
        publisher.upload_video_binary("https://example.com/upload", "/path/to/nonexistent/video.mp4")


def test_tiktok_publisher_full_pipeline_init_and_put_upload():
    """Vérifie la séquence complète : POST init puis HTTP PUT binaire."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_video = os.path.join(tmpdir, "predication.mp4")
        video_bytes = b"MP4_PREDICATION_GOSPEL_DATA" * 50
        with open(fake_video, "wb") as f:
            f.write(video_bytes)

        file_size = len(video_bytes)
        upload_target = "https://open-upload.tiktokapis.com/video/?id=predic_01"

        # Mock pour Init (POST)
        init_response_data = json.dumps({
            "data": {
                "upload_url": upload_target,
                "publish_id": "v_pub_gospel_777"
            },
            "error": {"code": "ok", "message": ""}
        }).encode("utf-8")

        mock_init_resp = MagicMock()
        mock_init_resp.status = 200
        mock_init_resp.read.return_value = init_response_data
        mock_init_resp.__enter__.return_value = mock_init_resp

        # Mock pour PUT binaire
        mock_put_resp = MagicMock()
        mock_put_resp.status = 200
        mock_put_resp.read.return_value = b""
        mock_put_resp.__enter__.return_value = mock_put_resp

        def urlopen_side_effect(req, *args, **kwargs):
            if req.get_method() == "POST":
                return mock_init_resp
            elif req.get_method() == "PUT":
                return mock_put_resp
            raise ValueError(f"Méthode inattendue : {req.get_method()}")

        publisher = TikTokPublisher(access_token="valid_tiktok_secret_token")
        growth_package = {
            "hook_banner": "LE MIRACLE QUE TU ATTENDS ARRIVE ⚡",
            "full_post_text": "Déclare ta victoire en Jésus-Christ ! #foi #miracle",
            "estimated_retention": "88%"
        }

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect) as mock_urlopen:
            res = publisher.publish_clip(fake_video, growth_package, privacy_level="PUBLIC_TO_EVERYONE")

            assert res["status"] == "success"
            assert res["method"] == "official_api"
            assert res["publish_id"] == "v_pub_gospel_777"
            assert res["upload_url"] == upload_target
            assert res["upload_status"] == 200
            assert mock_urlopen.call_count == 2


def test_tiktok_publisher_api_network_error_graceful_handling():
    """Vérifie que les pannes réseau TikTok API sont capturées proprement sans crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_video = os.path.join(tmpdir, "error_test.mp4")
        with open(fake_video, "wb") as f:
            f.write(b"data")

        publisher = TikTokPublisher(access_token="valid_token")
        growth_package = {"hook_banner": "Hook", "full_post_text": "Caption"}

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network unreachable")):
            res = publisher.publish_clip(fake_video, growth_package)

            assert res["status"] == "error"
            assert "Network unreachable" in res["error"]
            # Le fichier payload doit tout de même exister pour rejeu
            assert os.path.exists(res["payload_file"])


# =====================================================================
# Tests GrowthOptimizer (P0 KeyError karl_studio_link & location_focus)
# =====================================================================

def test_growth_optimizer_export_summary_no_key_error():
    """Vérifie que export_summary_sheet ne plante pas avec KeyError quand karl_studio_link est absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sheet_path = os.path.join(tmpdir, "summary.txt")
        growth = GrowthOptimizer()

        # Package minimal sans 'karl_studio_link'
        minimal_package = {
            "hook_banner": "FAIS CETTE PRIÈRE PUISSANTE 🙏",
            "full_post_text": "Prière du matin pour la protection divine",
            "recommended_schedule": ["05h30 - 06h45 GMT"],
            "estimated_retention": "82%",
            "cta": "Écris 'AMEN'"
        }

        growth.export_summary_sheet(minimal_package, sheet_path)
        assert os.path.exists(sheet_path)

        with open(sheet_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Doit contenir le lien par défaut vers Karl Studio
        assert "https://digrekarlito11-eng.github.io/karl-studio/" in content
        # Doit mentionner location_focus
        assert "location_focus" in content or "Côte d'Ivoire (GMT / Abidjan)" in content


def test_growth_optimizer_generate_package_contains_link_and_focus():
    """Vérifie que generate_growth_package produit un dictionnaire avec karl_studio_link et location_focus."""
    growth = GrowthOptimizer()
    clip_info = {
        "text": "Seigneur Jésus donne-moi la force de vaincre l'épreuve",
        "first_sentence": "Seigneur Jésus donne-moi la force",
        "score": 15
    }
    package = growth.generate_growth_package(clip_info, "Prédication Pasteur")

    assert "karl_studio_link" in package
    assert package["karl_studio_link"] == "https://digrekarlito11-eng.github.io/karl-studio/"
    assert "location_focus" in package
    assert "Côte d'Ivoire" in package["location_focus"]


# =====================================================================
# Tests TikTokNotifier (DevOps-Bot Instant Notifications)
# =====================================================================

def test_notifier_with_webhook():
    """Vérifie l'envoi de la notification Webhook avec le payload attendu."""
    clip_data = {
        "video_path": "output/tiktok_predication_clip_1.mp4",
        "hook": "CETTE PAROLE VA CHANGER TA VIE ✨",
        "duration": 42.5,
        "retention": "86%",
        "caption": "Reçois la grâce de Dieu dès maintenant. Écris AMEN."
    }

    notifier = TikTokNotifier(webhook_url="https://discord.com/api/webhooks/test-karl")

    mock_resp = MagicMock()
    mock_resp.status = 204
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        notifier.notify_clip_ready(clip_data, total_clips=1)

        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://discord.com/api/webhooks/test-karl"

        payload = json.loads(req.data.decode("utf-8"))
        assert "content" in payload
        assert "CETTE PAROLE VA CHANGER TA VIE" in payload["content"]
        assert "tiktok_predication_clip_1.mp4" in payload["content"]


def test_notifier_without_webhook_does_not_call_network():
    """Vérifie qu'aucun appel HTTP n'est tenté si aucun webhook n'est configuré."""
    clip_data = {
        "video_path": "output/test.mp4",
        "hook": "TEST",
        "duration": 30,
        "retention": "80%",
        "caption": "Caption"
    }
    with patch.dict(os.environ, {}, clear=True):
        notifier = TikTokNotifier(webhook_url=None)
        with patch("urllib.request.urlopen") as mock_urlopen:
            notifier.notify_clip_ready(clip_data, total_clips=1)
            mock_urlopen.assert_not_called()


def test_notifier_webhook_error_captured():
    """Vérifie que les erreurs de webhook (ex. timeout) sont capturées sans exception."""
    clip_data = {
        "video_path": "output/test.mp4",
        "hook": "TEST",
        "duration": 30,
        "retention": "80%",
        "caption": "Caption"
    }
    notifier = TikTokNotifier(webhook_url="https://invalid-webhook.com")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Timed out")):
        # Ne doit pas lever d'exception
        notifier.notify_clip_ready(clip_data, total_clips=1)


# =====================================================================
# Tests CLI Arguments (main.py)
# =====================================================================

def test_main_cli_arg_parsing():
    """Vérifie que les arguments CLI de main.py sont correctement acceptés."""
    test_args = [
        "main.py",
        "--url", "https://www.youtube.com/watch?v=sample123",
        "--clips", "2",
        "--theme", "gospel",
        "--watermark", "@karl.studio",
        "--publish", "draft",
        "--no-progress-bar",
        "--webhook", "https://discord.com/api/webhooks/karl"
    ]
    with patch("sys.argv", test_args):
        with patch("main.TikTokPipeline") as mock_pipeline_cls:
            mock_instance = MagicMock()
            mock_pipeline_cls.return_value = mock_instance

            main.main()

            mock_pipeline_cls.assert_called_once_with(
                output_dir="output",
                theme_name="gospel",
                watermark="@karl.studio",
                with_progress_bar=False,
                webhook_url="https://discord.com/api/webhooks/karl",
                publish_mode="draft"
            )
            mock_instance.process_url.assert_called_once_with(
                "https://www.youtube.com/watch?v=sample123",
                top_k=2
            )


def test_main_cli_demo_flag():
    """Vérifie que main.py --demo invoque bien run_synthetic_demo avec les bons paramètres."""
    with patch("sys.argv", ["main.py", "--demo", "--theme", "gospel", "--watermark", "@karl.studio"]):
        with patch("main.run_synthetic_demo") as mock_demo:
            main.main()
            mock_demo.assert_called_once_with("output", theme="gospel", watermark="@karl.studio")


def test_main_cli_missing_source_exits():
    """Vérifie que main.py sort avec le code 1 si aucune source (url, video, batch, demo) n'est donnée."""
    with patch("sys.argv", ["main.py"]):
        with pytest.raises(SystemExit) as excinfo:
            main.main()
        assert excinfo.value.code == 1
