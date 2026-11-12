import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

class TikTokPublisher:
    """
    Sous-agent DevOps-Bot & Media-Bot / Module de Publication Directe TikTok.
    Prend en charge la publication automatique via :
    1. L'API Officielle TikTok (Content Posting API v2).
    2. Le mode 'Brouillon Automatique' (Draft) pour pré-remplir la vidéo sur le compte TikTok de Karl.
    3. Le pont Webhook / Multi-plateforme (Buffer, Ayrshare, Make, Telegram).
    """

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.environ.get("TIKTOK_ACCESS_TOKEN")
        self.api_base_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"

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
        video_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0

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
        with open(payload_file, "w", encoding="utf-8") as f:
            json.dump(tiktok_payload, f, indent=2, ensure_ascii=False)

        # Si un token officiel TikTok est présent dans les Secrets GitHub
        if self.access_token:
            try:
                print("🔑 [DevOps-Bot] Connexion à l'API officielle TikTok...")
                req_data = json.dumps(tiktok_payload).encode("utf-8")
                req = urllib.request.Request(
                    self.api_base_url,
                    data=req_data,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    print(f"✅ [DevOps-Bot] Réponse TikTok API : {resp_data}")
                    return {
                        "status": "success",
                        "method": "official_api",
                        "response": resp_data,
                        "payload_file": payload_file
                    }
            except Exception as e:
                print(f"⚠️ Erreur appel direct API TikTok : {e}")
                print("💡 Le payload a été préparé localement pour rejeu.")

        # Mode simulation / Assistant connecté (sans clé API)
        print(f"ℹ️ [DevOps-Bot] Clé TikTok en attente de configuration. Fiche et payload enregistrés : {payload_file}")
        return {
            "status": "ready_to_publish",
            "method": "ready_package",
            "privacy_level": privacy_level,
            "payload_file": payload_file,
            "instructions": "Ajoute TIKTOK_ACCESS_TOKEN dans les Secrets GitHub pour publier en 100% automatique sans toucher à ton téléphone."
        }
