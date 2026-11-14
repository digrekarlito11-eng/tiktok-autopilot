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


def test_parse_and_prepare_cookies_various_formats():
    """Vérifie la robustesse du parseur de cookies multi-formats et la détection d'anomalies."""
    from src.tiktok_studio_uploader import TikTokStudioUploader

    # 1. Raw token
    c1 = TikTokStudioUploader.parse_and_prepare_cookies("a1b2c3d4e5")
    assert len(c1) == 2
    assert c1[0]["name"] == "sessionid"
    assert c1[0]["value"] == "a1b2c3d4e5"
    assert c1[1]["name"] == "sessionid_ss"

    # 2. Key=value
    c2 = TikTokStudioUploader.parse_and_prepare_cookies("sessionid=test_value_123")
    assert len(c2) == 2
    assert c2[0]["value"] == "test_value_123"

    # 3. Multi-cookie header
    c3 = TikTokStudioUploader.parse_and_prepare_cookies("sessionid=val1; sid_tt=val2; uid_tt=val3")
    assert len(c3) == 4
    names = [c["name"] for c in c3]
    assert "sessionid" in names and "sessionid_ss" in names and "sid_tt" in names

    # 4. Cookie-Editor JSON with sameSite & expirationDate
    c4_json = json.dumps([
        {
            "name": "sessionid",
            "value": "json_val",
            "domain": ".tiktok.com",
            "path": "/",
            "sameSite": "no_restriction",
            "secure": False,
            "httpOnly": True,
            "expirationDate": 1800000000.5,
        },
        {
            "name": "sid_guard",
            "value": "guard_val",
            "sameSite": "strict",
            "httpOnly": False,
        },
    ])
    c4 = TikTokStudioUploader.parse_and_prepare_cookies(c4_json)
    c4_map = {c["name"]: c for c in c4}
    assert {"sessionid", "sessionid_ss", "sid_guard"} <= set(c4_map.keys())
    assert c4_map["sessionid"]["sameSite"] == "None"
    assert c4_map["sessionid"]["secure"] is True  # forced for SameSite=None
    assert c4_map["sessionid"]["expires"] == 1800000000
    assert c4_map["sid_guard"]["sameSite"] == "Strict"
    assert c4_map["sid_guard"]["httpOnly"] is False

    # 5. Playwright storageState JSON
    c5 = TikTokStudioUploader.parse_and_prepare_cookies(
        json.dumps({"cookies": [{"name": "sessionid", "value": "ss_val"}], "origins": []})
    )
    assert any(c["name"] == "sessionid" and c["value"] == "ss_val" for c in c5)

    # 6. Netscape cookies.txt (including #HttpOnly_)
    netscape_txt = (
        "# Netscape HTTP Cookie File\n"
        "#HttpOnly_.tiktok.com\tTRUE\t/\tTRUE\t1800000000\tsessionid\tnetscape_sess\n"
        ".tiktok.com\tTRUE\t/\tTRUE\t1800000000\tsid_tt\tnetscape_sid\n"
    )
    c6 = TikTokStudioUploader.parse_and_prepare_cookies(netscape_txt)
    c6_map = {c["name"]: c for c in c6}
    assert c6_map["sessionid"]["value"] == "netscape_sess"
    assert c6_map["sessionid"]["httpOnly"] is True
    assert c6_map["sid_tt"]["value"] == "netscape_sid"
    assert "sessionid_ss" in c6_map

    # 7. Chrome DevTools row paste
    devtools_txt = "Name\tValue\tDomain\tPath\nsessionid\tdev_sess\t.tiktok.com\t/\nsid_guard\tdev_guard\t.tiktok.com\t/"
    c7 = TikTokStudioUploader.parse_and_prepare_cookies(devtools_txt)
    c7_map = {c["name"]: c for c in c7}
    assert c7_map["sessionid"]["value"] == "dev_sess"
    assert c7_map["sid_guard"]["value"] == "dev_guard"

    # 8. Invalid URL, truncated JSON, and multi-line non-cookie text
    assert TikTokStudioUploader.parse_and_prepare_cookies("https://www.tiktok.com/tiktokstudio/upload") == []
    assert TikTokStudioUploader.parse_and_prepare_cookies('[{"name": "sessionid"') == []
    assert TikTokStudioUploader.parse_and_prepare_cookies("hello world\nnot a cookie") == []


def test_tiktok_studio_uploader_rejects_export_without_sessionid(tmp_path):
    """Vérifie que l'uploader refuse proprement un export JSON sans cookie sessionid."""
    from src.tiktok_studio_uploader import TikTokStudioUploader

    video_file = tmp_path / "clip.mp4"
    video_file.write_bytes(b"\x00" * 128)
    no_sess_json = json.dumps([{"name": "ttwid", "value": "guest_only"}])

    uploader = TikTokStudioUploader(session_id=no_sess_json, screenshots_dir=str(tmp_path / "screens"))
    res = uploader.upload(str(video_file), "Légende test", mode="draft")

    assert res["status"] == "auth_error"
    assert "sessionid" in res["error"]


def test_tiktok_studio_uploader_draft_save_flow_mock(tmp_path):
    """Vérifie le flux complet TikTokStudioUploader (warm-up, upload, save_draft_button) avec Playwright simulé."""
    import sys
    import types
    from src.tiktok_studio_uploader import TikTokStudioUploader

    video_file = tmp_path / "clip.mp4"
    video_file.write_bytes(b"MP4DATA")
    screens_dir = tmp_path / "screens"

    class FakeLocator:
        def __init__(self, selector, page):
            self.selector = selector
            self.page = page

        def count(self):
            if self.selector in ("input[type='file']", ".public-DraftEditor-content", "button[data-e2e='save_draft_button']"):
                return 1
            return 0

        @property
        def first(self):
            return self

        def wait_for(self, **kwargs):
            return None

        def is_visible(self):
            if self.selector == "button[data-e2e='save_draft_button']" and self.page.draft_saved:
                return False
            return self.count() > 0

        def set_input_files(self, path):
            self.page.uploaded_path = path

        def scroll_into_view_if_needed(self):
            return None

        def get_attribute(self, attr):
            return None

        def click(self, **kwargs):
            if self.selector == "button[data-e2e='save_draft_button']":
                self.page.draft_saved = True
                self.page.url = "https://www.tiktok.com/tiktokstudio/content"

    class FakePage:
        def __init__(self):
            self.url = "about:blank"
            self.frames = []
            self.draft_saved = False
            self.uploaded_path = None
            self.visited_urls = []
            self.keyboard = MagicMock()

        def set_default_timeout(self, ms):
            pass

        def on(self, event, cb):
            pass

        def goto(self, url, **kwargs):
            self.visited_urls.append(url)
            self.url = url

        def title(self):
            return "TikTok Studio"

        def locator(self, sel):
            return FakeLocator(sel, self)

        def inner_text(self, sel):
            if self.draft_saved:
                return "Enregistré dans les brouillons"
            return "100% Téléchargé"

        def evaluate(self, script):
            return None

        def screenshot(self, path, **kwargs):
            Path(path).write_bytes(b"PNG")

    fake_page = FakePage()
    fake_context = MagicMock()
    fake_context.new_page.return_value = fake_page
    fake_browser = MagicMock()
    fake_browser.version = "131.0.6778.85"
    fake_browser.new_context.return_value = fake_context
    fake_p = MagicMock()
    fake_p.chromium.launch.return_value = fake_browser

    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = fake_p
    fake_cm.__exit__.return_value = False

    fake_sync_mod = types.ModuleType("playwright.sync_api")
    fake_sync_mod.sync_playwright = lambda: fake_cm
    fake_pw_mod = types.ModuleType("playwright")
    fake_pw_mod.sync_api = fake_sync_mod

    cookies_json = json.dumps([
        {"name": "sessionid", "value": "valid_sess"},
        {"name": "sid_tt", "value": "valid_sid"},
    ])

    with patch.dict(sys.modules, {"playwright": fake_pw_mod, "playwright.sync_api": fake_sync_mod}):
        with patch("time.sleep", return_value=None):
            uploader = TikTokStudioUploader(session_id=cookies_json, screenshots_dir=str(screens_dir))
            res = uploader.upload(str(video_file), "Parole bénie #chretien", mode="draft")

    assert res["status"] == "success"
    assert res["action_clicked"] is True
    assert res["success_detected"] is True
    assert fake_page.uploaded_path == str(video_file.resolve())
    assert fake_page.visited_urls == [
        "https://www.tiktok.com/?lang=fr",
        "https://www.tiktok.com/tiktokstudio/upload?lang=fr",
    ]
    assert (screens_dir / "04_action_clicked.png").exists()
    assert (screens_dir / "05_final_state.png").exists()


def test_workflow_autopilot_247_yaml_validity():
    """Vérifie la validité YAML et les sécurités de .github/workflows/autopilot_247.yml."""
    import yaml

    yaml_path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "autopilot_247.yml"
    assert yaml_path.exists()
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    on_key = True if True in data else "on"
    inputs = data[on_key]["workflow_dispatch"]["inputs"]
    assert "use_warp" in inputs
    assert inputs["use_warp"]["default"] is True
    assert inputs["publish_mode"]["default"] == "public"

    for job_name in ("autopilot-cycle", "autopilot-cycle-arm"):
        steps = data["jobs"][job_name]["steps"]
        run_step = next(s for s in steps if "Exécution" in s.get("name", ""))
        assert "'public'" in run_step["env"]["PUBLISH_MODE"]

    steps = data["jobs"]["autopilot-cycle"]["steps"]
    history_step = next(s for s in steps if "Historique" in s.get("name", ""))
    assert "git pull --rebase origin main" in history_step["run"]


def test_workflow_publish_drafts_and_generate_public_defaults():
    """Vérifie la validité YAML de publish_drafts.yml et la valeur par défaut public de generate_tiktok.yml."""
    import yaml

    root = Path(__file__).resolve().parent.parent
    gen_path = root / ".github" / "workflows" / "generate_tiktok.yml"
    pub_drafts_path = root / ".github" / "workflows" / "publish_drafts.yml"
    assert gen_path.exists()
    assert pub_drafts_path.exists()

    with open(gen_path, "r", encoding="utf-8") as f:
        gen_data = yaml.safe_load(f)
    gen_on = True if True in gen_data else "on"
    assert gen_data[gen_on]["workflow_dispatch"]["inputs"]["publish_mode"]["default"] == "public"

    with open(pub_drafts_path, "r", encoding="utf-8") as f:
        pub_data = yaml.safe_load(f)
    pub_on = True if True in pub_data else "on"
    pub_inputs = pub_data[pub_on]["workflow_dispatch"]["inputs"]
    assert pub_inputs["max_drafts"]["default"] == "30"
    assert "publish-drafts" in pub_data["jobs"]


def test_tiktok_studio_uploader_public_mode_escape_and_modal_mock(tmp_path):
    """Vérifie le mode public (Escape menu hashtag, clic Publier, modale de confirmation) avec Playwright simulé."""
    import types
    from src.tiktok_studio_uploader import TikTokStudioUploader

    video_file = tmp_path / "clip_pub.mp4"
    video_file.write_bytes(b"MP4DATA")
    screens_dir = tmp_path / "screens_pub"

    class FakePublicLocator:
        def __init__(self, selector, page):
            self.selector = selector
            self.page = page

        def count(self):
            if self.selector in ("input[type='file']", ".public-DraftEditor-content", "button[data-e2e='post_video_button']"):
                return 1
            if self.selector == "div[role='dialog'] button:has-text('Publier maintenant')" and self.page.modal_open:
                return 1
            return 0

        @property
        def first(self):
            return self

        def nth(self, idx):
            return self

        def wait_for(self, **kwargs):
            return None

        def is_visible(self):
            if self.selector == "button[data-e2e='post_video_button']" and self.page.published:
                return False
            return self.count() > 0

        def set_input_files(self, path):
            self.page.uploaded_path = path

        def scroll_into_view_if_needed(self):
            return None

        def evaluate(self, script):
            return None

        def get_attribute(self, attr):
            return None

        def click(self, **kwargs):
            if self.selector == "button[data-e2e='post_video_button']":
                self.page.modal_open = True
            elif "Publier maintenant" in self.selector:
                self.page.modal_open = False
                self.page.published = True
                self.page.url = "https://www.tiktok.com/tiktokstudio/content"

    class FakePublicPage:
        def __init__(self):
            self.url = "about:blank"
            self.frames = []
            self.modal_open = False
            self.published = False
            self.uploaded_path = None
            self.keyboard = MagicMock()

        def set_default_timeout(self, ms):
            pass

        def on(self, event, cb):
            pass

        def goto(self, url, **kwargs):
            self.url = url

        def title(self):
            return "TikTok Studio"

        def locator(self, sel):
            return FakePublicLocator(sel, self)

        def inner_text(self, sel):
            if self.published:
                return "Votre vidéo est en cours de publication sur TikTok"
            return "100% Téléchargé"

        def evaluate(self, script):
            return None

        def screenshot(self, path, **kwargs):
            Path(path).write_bytes(b"PNG")

    fake_page = FakePublicPage()
    fake_context = MagicMock()
    fake_context.new_page.return_value = fake_page
    fake_browser = MagicMock()
    fake_browser.version = "131.0.6778.85"
    fake_browser.new_context.return_value = fake_context
    fake_p = MagicMock()
    fake_p.chromium.launch.return_value = fake_browser
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = fake_p
    fake_cm.__exit__.return_value = False

    fake_sync_mod = types.ModuleType("playwright.sync_api")
    fake_sync_mod.sync_playwright = lambda: fake_cm
    fake_pw_mod = types.ModuleType("playwright")
    fake_pw_mod.sync_api = fake_sync_mod

    cookies_json = json.dumps([{"name": "sessionid", "value": "sess"}, {"name": "sid_tt", "value": "sid"}])

    with patch.dict(sys.modules, {"playwright": fake_pw_mod, "playwright.sync_api": fake_sync_mod}):
        with patch("time.sleep", return_value=None):
            uploader = TikTokStudioUploader(session_id=cookies_json, screenshots_dir=str(screens_dir))
            res = uploader.upload(str(video_file), "Message fort #jesus", mode="public")

    assert res["status"] == "success"
    assert res["mode"] == "public"
    assert res["action_clicked"] is True
    assert res["success_detected"] is True
    fake_page.keyboard.press.assert_any_call("Escape")
    assert fake_page.published is True


def test_publish_all_drafts_multi_and_skip_failing_row_mock(tmp_path):
    """Vérifie publish_all_drafts : boucle sur les brouillons, saut d'une ligne bloquée et bilan final."""
    import types
    from src.tiktok_studio_uploader import TikTokStudioUploader

    screens_dir = tmp_path / "draft_screens"

    class FakeDraftsLocator:
        def __init__(self, selector, page):
            self.selector = selector
            self.page = page

        def count(self):
            if self.selector.startswith("[data-autopilot-edit-idx='"):
                idx = int(self.selector.split("'")[1])
                return 1 if (not self.page.in_editor and idx < len(self.page.draft_rows)) else 0
            if self.selector == "button[data-e2e='post_video_button']" and self.page.in_editor:
                return 1
            return 0

        @property
        def first(self):
            return self

        def nth(self, idx):
            return self

        def is_visible(self):
            return self.count() > 0

        def scroll_into_view_if_needed(self):
            return None

        def get_attribute(self, attr):
            return None

        def click(self, **kwargs):
            if self.selector.startswith("[data-autopilot-edit-idx='"):
                idx = int(self.selector.split("'")[1])
                self.page.active_draft = self.page.draft_rows[idx]
                self.page.in_editor = True
                self.page.url = "https://www.tiktok.com/tiktokstudio/upload?from=draft"
            elif self.selector == "button[data-e2e='post_video_button']":
                sig = self.page.active_draft["signature"]
                if "Bloqué" in sig:
                    # Reste sur place sans confirmation pour simuler une ligne en échec
                    return
                self.page.draft_rows = [r for r in self.page.draft_rows if r["signature"] != sig]
                self.page.published_count += 1
                self.page.in_editor = False
                self.page.url = "https://www.tiktok.com/tiktokstudio/content?tab=draft"

    class FakeDraftsPage:
        def __init__(self):
            self.url = "about:blank"
            self.in_editor = False
            self.published_count = 0
            self.active_draft = None
            self.draft_rows = [
                {"idx": 0, "signature": "Brouillon 1 #foi 22:54", "strategy": "explicit"},
                {"idx": 1, "signature": "Brouillon Bloqué 22:50", "strategy": "explicit"},
                {"idx": 2, "signature": "Brouillon 3 #mariage 22:48", "strategy": "explicit"},
            ]

        def set_default_timeout(self, ms):
            pass

        def on(self, event, cb):
            pass

        def goto(self, url, **kwargs):
            self.url = url
            if "content" in url:
                self.in_editor = False

        def reload(self, **kwargs):
            pass

        def locator(self, sel):
            return FakeDraftsLocator(sel, self)

        def inner_text(self, sel):
            if self.in_editor:
                return "Paramètres Quand publier"
            return f"Publications {self.published_count}\nBrouillons {len(self.draft_rows)}"

        def evaluate(self, script):
            if "findEditTargetInRow" in script:
                return [
                    {"idx": i, "signature": r["signature"], "strategy": r["strategy"]}
                    for i, r in enumerate(self.draft_rows)
                ]
            return None

        def screenshot(self, path, **kwargs):
            Path(path).write_bytes(b"PNG")

    fake_page = FakeDraftsPage()
    fake_context = MagicMock()
    fake_context.new_page.return_value = fake_page
    fake_context.pages = [fake_page]
    fake_browser = MagicMock()
    fake_browser.version = "131.0.6778.85"
    fake_browser.new_context.return_value = fake_context
    fake_p = MagicMock()
    fake_p.chromium.launch.return_value = fake_browser
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = fake_p
    fake_cm.__exit__.return_value = False

    fake_sync_mod = types.ModuleType("playwright.sync_api")
    fake_sync_mod.sync_playwright = lambda: fake_cm
    fake_pw_mod = types.ModuleType("playwright")
    fake_pw_mod.sync_api = fake_sync_mod

    cookies_json = json.dumps([{"name": "sessionid", "value": "sess"}, {"name": "sid_tt", "value": "sid"}])

    with patch.dict(sys.modules, {"playwright": fake_pw_mod, "playwright.sync_api": fake_sync_mod}):
        with patch("time.sleep", return_value=None):
            uploader = TikTokStudioUploader(session_id=cookies_json, screenshots_dir=str(screens_dir))
            res = uploader.publish_all_drafts(max_count=10, pause_seconds=0.0)

    assert res["status"] == "partial_success"
    assert res["publications_before"] == 0
    assert res["drafts_before"] == 3
    assert res["published_count"] == 2
    assert res["failed_count"] == 1
    assert res["publications_after"] == 2
    assert res["drafts_after"] == 1
    assert (screens_dir / "drafts_before.png").exists()
    assert (screens_dir / "drafts_after.png").exists()
    assert (screens_dir / "posts_after.png").exists()


def test_draft_publisher_cli_writes_report_and_handles_empty(tmp_path):
    """Vérifie le script CLI src.draft_publisher et l'export du rapport JSON."""
    from src import draft_publisher

    report_dir = tmp_path / "out_drafts"
    mock_result = {
        "status": "success",
        "publications_before": 0,
        "drafts_before": 22,
        "publications_after": 22,
        "drafts_after": 0,
        "published_count": 22,
        "failed_count": 0,
    }

    with patch("src.draft_publisher.TikTokStudioUploader") as mock_cls:
        mock_cls.return_value.publish_all_drafts.return_value = mock_result
        with patch("sys.argv", ["draft_publisher.py", "--max", "30", "--screenshots-dir", str(report_dir)]):
            draft_publisher.main()

    report_json = report_dir / "draft_publish_report.json"
    assert report_json.exists()
    saved = json.loads(report_json.read_text(encoding="utf-8"))
    assert saved["published_count"] == 22
    assert saved["status"] == "success"


def test_publish_all_drafts_handles_transient_zero_hydration_flicker(tmp_path):
    """Vérifie qu'un affichage transitoire 'Brouillons 0' avant chargement XHR n'arrête pas la boucle."""
    import types
    from src.tiktok_studio_uploader import TikTokStudioUploader

    screens_dir = tmp_path / "draft_flicker_screens"

    class FlickerLocator:
        def __init__(self, selector, page):
            self.selector = selector
            self.page = page

        def count(self):
            if self.selector.startswith("[data-autopilot-edit-idx='"):
                idx = int(self.selector.split("'")[1])
                return 1 if (not self.page.in_editor and idx < len(self.page.draft_rows)) else 0
            if self.selector == "button[data-e2e='post_video_button']" and self.page.in_editor:
                return 1
            return 0

        @property
        def first(self):
            return self

        def nth(self, idx):
            return self

        def is_visible(self):
            return self.count() > 0

        def scroll_into_view_if_needed(self):
            return None

        def get_attribute(self, attr):
            return None

        def click(self, **kwargs):
            if self.selector.startswith("[data-autopilot-edit-idx='"):
                idx = int(self.selector.split("'")[1])
                self.page.active_draft = self.page.draft_rows[idx]
                self.page.in_editor = True
                self.page.url = "https://www.tiktok.com/tiktokstudio/upload?from=draft"
            elif self.selector == "button[data-e2e='post_video_button']":
                sig = self.page.active_draft["signature"]
                self.page.draft_rows = [r for r in self.page.draft_rows if r["signature"] != sig]
                self.page.published_count += 1
                self.page.in_editor = False
                self.page.url = "https://www.tiktok.com/tiktokstudio/content?tab=draft"

    class FlickerPage:
        def __init__(self):
            self.url = "about:blank"
            self.in_editor = False
            self.published_count = 0
            self.active_draft = None
            self.loading_polls_left = 0
            self.draft_rows = [
                {"idx": 0, "signature": "Brouillon A 22:50", "strategy": "right_cluster_first(3)"},
                {"idx": 1, "signature": "Brouillon B 22:48", "strategy": "right_cluster_first(3)"},
                {"idx": 2, "signature": "Brouillon C 22:45", "strategy": "right_cluster_first(3)"},
            ]

        def set_default_timeout(self, ms):
            pass

        def on(self, event, cb):
            pass

        def goto(self, url, **kwargs):
            self.url = url
            if "tab=draft" in url:
                self.in_editor = False
                # Simule 2 lectures transitoires "Brouillons 0" pendant le chargement React
                if self.published_count > 0:
                    self.loading_polls_left = 2

        def reload(self, **kwargs):
            self.loading_polls_left = 0

        def locator(self, sel):
            return FlickerLocator(sel, self)

        def inner_text(self, sel):
            if self.in_editor:
                return "Paramètres Quand publier"
            if self.loading_polls_left > 0:
                return f"Publications {self.published_count}\nBrouillons 0"
            return f"Publications {self.published_count}\nBrouillons {len(self.draft_rows)}"

        def evaluate(self, script):
            if "findEditTargetInRow" in script:
                if self.loading_polls_left > 0:
                    self.loading_polls_left -= 1
                    return []
                return [
                    {"idx": i, "signature": r["signature"], "strategy": r["strategy"]}
                    for i, r in enumerate(self.draft_rows)
                ]
            return None

        def screenshot(self, path, **kwargs):
            Path(path).write_bytes(b"PNG")

    fake_page = FlickerPage()
    fake_context = MagicMock()
    fake_context.new_page.return_value = fake_page
    fake_context.pages = [fake_page]
    fake_browser = MagicMock()
    fake_browser.version = "131.0.6778.85"
    fake_browser.new_context.return_value = fake_context
    fake_p = MagicMock()
    fake_p.chromium.launch.return_value = fake_browser
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = fake_p
    fake_cm.__exit__.return_value = False

    fake_sync_mod = types.ModuleType("playwright.sync_api")
    fake_sync_mod.sync_playwright = lambda: fake_cm
    fake_pw_mod = types.ModuleType("playwright")
    fake_pw_mod.sync_api = fake_sync_mod

    cookies_json = json.dumps([{"name": "sessionid", "value": "sess"}, {"name": "sid_tt", "value": "sid"}])

    with patch.dict(sys.modules, {"playwright": fake_pw_mod, "playwright.sync_api": fake_sync_mod}):
        with patch("time.sleep", return_value=None):
            uploader = TikTokStudioUploader(session_id=cookies_json, screenshots_dir=str(screens_dir))
            res = uploader.publish_all_drafts(max_count=10, pause_seconds=0.0)

    assert res["status"] == "success"
    assert res["published_count"] == 3
    assert res["drafts_after"] == 0
    assert res["publications_after"] == 3

