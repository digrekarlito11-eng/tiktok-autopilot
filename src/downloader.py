import os
import sys
import json
import subprocess
from typing import Dict, Any, Optional

class VideoDownloader:
    """
    Sous-agent Media-Bot / Composant de téléchargement.
    Gère la récupération de vidéos sources (YouTube, podcasts, web) via yt-dlp.
    Extrait les sous-titres natifs pour gagner un temps précieux (0.5s vs plusieurs minutes).
    """

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def download(self, url: str) -> Dict[str, Any]:
        """
        Télécharge la vidéo au format MP4 optimal (max 1080p pour le traitement 9:16).
        Récupère également les sous-titres en français ou anglais si disponibles.
        """
        print(f"📥 [Media-Bot] Analyse du lien source : {url}")
        
        # Obtenir les métadonnées de la vidéo sans la télécharger d'abord
        info_cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            url
        ]
        
        try:
            result = subprocess.run(info_cmd, capture_output=True, text=True, check=True)
            video_info = json.loads(result.stdout)
            title = video_info.get("title", "video_source")
            video_id = video_info.get("id", "source")
            duration = video_info.get("duration", 0)
        except Exception as e:
            print(f"⚠️ Impossible d'extraire les infos détaillées via yt-dlp: {e}")
            title = "video_source"
            video_id = "source"
            duration = 0

        # Nettoyage du titre pour les fichiers
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()[:40].strip()
        output_template = os.path.join(self.download_dir, f"{video_id}_%(title).40s.%(ext)s")

        print(f"🎬 [Media-Bot] Téléchargement de la vidéo : '{title}' (Durée: {duration}s)")

        # Commande de téléchargement avec extraction automatique des sous-titres
        dl_cmd = [
            "yt-dlp",
            "--format", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs", "fr.*,en.*",
            "--sub-format", "vtt/best",
            "--no-playlist",
            "--output", output_template,
            url
        ]

        subprocess.run(dl_cmd, check=True)

        # Identifier les fichiers téléchargés
        video_file = None
        subtitle_file = None

        for fname in os.listdir(self.download_dir):
            if fname.startswith(video_id):
                full_p = os.path.join(self.download_dir, fname)
                if fname.endswith(".mp4"):
                    video_file = full_p
                elif fname.endswith(".vtt") or fname.endswith(".srt"):
                    # Privilégier les sous-titres FR
                    if "fr" in fname.lower() or not subtitle_file:
                        subtitle_file = full_p

        if not video_file:
            # Fallback chercher n'importe quel mp4 récent
            for fname in os.listdir(self.download_dir):
                if fname.endswith(".mp4"):
                    video_file = os.path.join(self.download_dir, fname)
                    break

        print(f"✅ [Media-Bot] Vidéo prête : {video_file}")
        if subtitle_file:
            print(f"📝 [Media-Bot] Sous-titres récupérés : {subtitle_file}")

        return {
            "title": title,
            "duration": duration,
            "video_path": video_file,
            "subtitle_path": subtitle_file,
            "url": url
        }
