import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional

class TikTokNotifier:
    """
    Sous-agent DevOps-Bot / Notificateur instantané.
    Avertit Karl dès qu'une vidéo TikTok est prête.
    Compatible Discord Webhook, Telegram Bot ou log formaté.
    """

    def __init__(self, webhook_url: Optional[str] = None, chat_id: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("TIKTOK_WEBHOOK_URL")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    def _build_payload(self, message_text: str) -> Dict[str, Any]:
        """Construit le payload JSON adapté au service (Telegram Bot API vs Discord/Slack Webhook)."""
        url_lower = (self.webhook_url or "").lower()
        if "api.telegram.org" in url_lower:
            payload: Dict[str, Any] = {"text": message_text, "content": message_text}
            parsed = urllib.parse.urlparse(self.webhook_url or "")
            qs = urllib.parse.parse_qs(parsed.query)
            chat_id = self.chat_id or (qs.get("chat_id", [None])[0])
            if chat_id:
                payload["chat_id"] = chat_id
            return payload
        return {"content": message_text}

    def notify_clip_ready(self, clip_data: Dict[str, Any], total_clips: int):
        hook = clip_data.get("hook", "")
        duration = clip_data.get("duration", 0)
        retention = clip_data.get("retention", "")
        video_filename = os.path.basename(clip_data.get("video_path", ""))

        message_text = (
            f"🎬 **Nouveau TikTok Prêt pour Karl !**\n"
            f"• **Fichier :** `{video_filename}`\n"
            f"• **Accroche (Hook) :** {hook}\n"
            f"• **Durée :** {duration}s | **Rétention estimée :** {retention}\n"
            f"• **Légende :**\n```\n{clip_data.get('caption', '')}\n```\n"
            f"🚀 Prêt à être publié sur TikTok !"
        )

        print("\n" + "="*55)
        print("🔔 [DevOps-Bot] Notification de fin de traitement :")
        print(f"Vidéo finalisée : {video_filename} ({duration}s)")
        print(f"Hook : {hook}")
        print("="*55 + "\n")

        if self.webhook_url:
            try:
                body = self._build_payload(message_text)
                payload = json.dumps(body).encode("utf-8")
                req = urllib.request.Request(
                    self.webhook_url,
                    data=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "TikTokAutopilot/1.0"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status in (200, 204):
                        print("✅ [DevOps-Bot] Notification Webhook envoyée sur le smartphone de Karl !")
            except Exception as e:
                print(f"⚠️ Erreur lors de l'envoi du webhook de notification : {e}")
