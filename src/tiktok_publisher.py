import os
import json
import time
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TikTokPublisher:
    """
    Sous-agent DevOps-Bot & Media-Bot / Module de Publication Directe TikTok.
    Prend en charge la publication automatique via :
    1. L'API Officielle TikTok (Content Posting API v2).
    2. Le mode 'Brouillon Automatique' (Draft) pour pré-remplir la vidéo sur le compte TikTok de Karl.
    3. Le pont Webhook / Multi-plateforme (Buffer, Ayrshare, Make, Telegram).
    """

    AUTH_ERROR_CODES = {
        "access_token_invalid",
        "token_expired",
        "invalid_token",
        "unauthorized",
        "scope_not_authorized",
    }

    def __init__(
        self,
        access_token: Optional[str] = None,
        session_id: Optional[str] = None,
        max_retries: int = 2,
        retry_delay: float = 0.01,
    ):
        self.access_token = access_token or os.environ.get("TIKTOK_ACCESS_TOKEN")
        self.session_id = session_id or os.environ.get("TIKTOK_SESSION_ID")
        self.api_base_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        self.max_retries = max(0, int(max_retries))
        self.retry_delay = max(0.0, float(retry_delay))
        if self.session_id:
            print("🔑 [DevOps-Bot] Session TikTok Studio détectée via TIKTOK_SESSION_ID (Méthode 1 active).")

    def _urlopen_with_retry(self, req: urllib.request.Request, timeout: float = 15):
        """
        Exécute une requête HTTP avec retries et backoff exponentiel sur erreurs transitoires (429, 5xx, URLError).
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                return urllib.request.urlopen(req, timeout=timeout)
            except urllib.error.HTTPError as e:
                last_exc = e
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    if self.retry_delay > 0:
                        time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                raise
            except urllib.error.URLError as e:
                last_exc = e
                if attempt < self.max_retries:
                    if self.retry_delay > 0:
                        time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                raise
        if last_exc:
            raise last_exc

    def upload_video_binary(self, upload_url: str, video_path: str, reject_empty: bool = False) -> int:
        """
        Phase 2 de l'API TikTok : Envoi du flux binaire vidéo via HTTP PUT.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Fichier vidéo introuvable pour téléversement : {video_path}")

        video_size = os.path.getsize(video_path)
        if video_size <= 0 and reject_empty:
            raise ValueError(f"Fichier vidéo vide (0 octet) refusé pour téléversement : {video_path}")

        with open(video_path, "rb") as f:
            video_bytes = f.read()

        headers = {
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
            "Content-Length": str(video_size)
        }

        req = urllib.request.Request(
            upload_url,
            data=video_bytes,
            headers=headers,
            method="PUT"
        )
        with self._urlopen_with_retry(req, timeout=60) as resp:
            status = getattr(resp, "status", 200)
            print(f"✅ [DevOps-Bot] Téléversement binaire TikTok réussi (HTTP {status})")
            return status

    def publish_clip(
        self,
        video_path: str,
        growth_package: Dict[str, Any],
        privacy_level: str = "SELF_ONLY"  # "PUBLIC_TO_EVERYONE" ou "SELF_ONLY" (Mode Brouillon sécurisé)
    ) -> Dict[str, Any]:
        """
        Publie ou programme la vidéo sur le compte TikTok de Karl.
        Si aucun Token TikTok n'est configuré, génère le payload prêt pour l'API et la passerelle.
        """
        video_filename = os.path.basename(video_path)
        video_exists = os.path.exists(video_path)
        video_size = os.path.getsize(video_path) if video_exists else 0

        post_caption = growth_package.get("full_post_text", "")
        hook = growth_package.get("hook_banner", "")

        print(f"\n📡 [DevOps-Bot] Préparation de la publication TikTok...")
        print(f"• Fichier : {video_filename} ({round(video_size / (1024*1024), 2)} Mo)")
        print(f"• Mode de publication : {'Direct Public 🚀' if privacy_level == 'PUBLIC_TO_EVERYONE' else 'Brouillon Privé (Draft) 📱'}")

        # Payload standard TikTok Content Posting API v2
        tiktok_payload = {
            "post_info": {
                "title": post_caption[:2200],  # Limite TikTok de caractères
                "privacy_level": privacy_level,
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
                "video_cover_timestamp_ms": 1500  # Image de couverture à 1.5s (sur le Hook)
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1
            }
        }

        # Sauvegarde locale du payload de publication
        payload_file = video_path.rsplit(".", 1)[0] + "_tiktok_payload.json"
        os.makedirs(os.path.dirname(payload_file) or ".", exist_ok=True)
        with open(payload_file, "w", encoding="utf-8") as f:
            json.dump(tiktok_payload, f, indent=2, ensure_ascii=False)

        if video_exists and video_size <= 0:
            err_msg = f"Fichier vidéo vide (0 octet) : {video_path}"
            logger.error(err_msg)
            return {
                "status": "error",
                "method": "official_api" if self.access_token else ("tiktok_studio_playwright" if self.session_id else "ready_package"),
                "error": err_msg,
                "payload_file": payload_file
            }

        # Si un token officiel TikTok est présent dans les Secrets GitHub
        if self.access_token:
            try:
                print("🔑 [DevOps-Bot] Connexion à l'API officielle TikTok (Phase 1: Init)...")
                req_data = json.dumps(tiktok_payload).encode("utf-8")
                req = urllib.request.Request(
                    self.api_base_url,
                    data=req_data,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    }
                )
                with self._urlopen_with_retry(req, timeout=15) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    print(f"✅ [DevOps-Bot] Réponse TikTok API Init : {resp_data}")

                error_obj = resp_data.get("error") if isinstance(resp_data.get("error"), dict) else {}
                error_code = str(error_obj.get("code") or "").strip()
                error_message = str(error_obj.get("message") or "").strip()

                data_obj = resp_data.get("data", {}) if isinstance(resp_data.get("data"), dict) else resp_data
                upload_url = data_obj.get("upload_url") or resp_data.get("upload_url")
                publish_id = data_obj.get("publish_id") or resp_data.get("publish_id")

                if error_code and error_code.lower() != "ok":
                    err_status = "auth_error" if error_code.lower() in self.AUTH_ERROR_CODES else "error"
                    err_detail = f"TikTok API error ({error_code}): {error_message}" if error_message else f"TikTok API error: {error_code}"
                    logger.warning("⚠️ [DevOps-Bot] %s", err_detail)
                    return {
                        "status": err_status,
                        "method": "official_api",
                        "error": err_detail,
                        "error_code": error_code,
                        "publish_id": publish_id,
                        "upload_url": upload_url,
                        "upload_status": None,
                        "response": resp_data,
                        "payload_file": payload_file
                    }

                upload_status = None
                if upload_url:
                    print(f"📤 [DevOps-Bot] Téléversement du binaire vidéo (Phase 2: PUT)...")
                    upload_status = self.upload_video_binary(upload_url, video_path, reject_empty=True)

                return {
                    "status": "success",
                    "method": "official_api",
                    "publish_id": publish_id,
                    "upload_url": upload_url,
                    "upload_status": upload_status,
                    "response": resp_data,
                    "payload_file": payload_file
                }
            except Exception as e:
                print(f"⚠️ Erreur appel direct API TikTok : {e}")
                print("💡 Le payload a été préparé localement pour rejeu.")
                return {
                    "status": "error",
                    "method": "official_api",
                    "error": str(e),
                    "payload_file": payload_file
                }

        # Si une session TikTok Studio (Méthode 1) est configurée
        if self.session_id:
            print("✨ [DevOps-Bot] Connexion à TikTok Studio Web active via TIKTOK_SESSION_ID.")
            try:
                try:
                    from .tiktok_studio_uploader import TikTokStudioUploader
                except ImportError:
                    from tiktok_studio_uploader import TikTokStudioUploader

                upload_mode = "public" if privacy_level == "PUBLIC_TO_EVERYONE" else "draft"
                uploader = TikTokStudioUploader(
                    session_id=self.session_id,
                    screenshots_dir=os.path.join(os.path.dirname(video_path) or "output", "screenshots")
                )
                upload_res = uploader.upload(
                    video_path=video_path,
                    caption=post_caption,
                    mode=upload_mode
                )
                upload_res["payload_file"] = payload_file
                upload_res["method"] = "tiktok_studio_playwright"
                return upload_res
            except Exception as e_uploader:
                print(f"⚠️ [DevOps-Bot] Exception lors de l'envoi Playwright : {e_uploader}")
                return {
                    "status": "error",
                    "method": "tiktok_studio_playwright",
                    "error": str(e_uploader),
                    "payload_file": payload_file
                }

        # Mode simulation / Assistant connecté (sans clé API ni session)
        print(f"ℹ️ [DevOps-Bot] Clé TikTok en attente de configuration. Fiche et payload enregistrés : {payload_file}")
        return {
            "status": "ready_to_publish",
            "method": "ready_package",
            "privacy_level": privacy_level,
            "payload_file": payload_file,
            "instructions": "Ajoute TIKTOK_ACCESS_TOKEN ou TIKTOK_SESSION_ID dans les Secrets GitHub pour publier en 100% automatique."
        }
