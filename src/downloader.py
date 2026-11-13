import os
import sys
import json
import uuid
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

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extrait les métadonnées de la vidéo via yt-dlp sans la télécharger.
        Invoque [sys.executable, "-m", "yt_dlp", ...] pour garantir l'utilisation
        du paquet dans l'environnement virtuel actif.
        """
        url = str(url).strip().strip("'\"").strip()
        info_cmd = [
            sys.executable, "-m", "yt_dlp",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            "--extractor-args", "youtube:player_client=tv,web_embedded;player_skip=webpage",
            "--dump-json",
            "--no-playlist",
            url
        ]

        # Support optionnel des cookies YouTube via secret d'environnement
        cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE")
        if cookies_file and os.path.exists(cookies_file):
            info_cmd.extend(["--cookies", cookies_file])

        try:
            result = subprocess.run(info_cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except Exception as e:
            print(f"⚠️ Impossible d'extraire les infos détaillées via yt-dlp: {e}")
            return {
                "title": "video_source",
                "id": "source",
                "duration": 0
            }

    def _download_video(self, url: str, output_template: str) -> None:
        """
        Télécharge le flux vidéo MP4 et les sous-titres via yt-dlp.
        Utilise [sys.executable, "-m", "yt_dlp", ...] pour la résilience de l'interpréteur.
        """
        url = str(url).strip().strip("'\"").strip()
        dl_cmd = [
            sys.executable, "-m", "yt_dlp",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            "--extractor-args", "youtube:player_client=tv,web_embedded;player_skip=webpage",
            "--format", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs", "fr.*",
            "--sub-format", "vtt/best",
            "--no-playlist",
            "--no-abort-on-error",
            "--merge-output-format", "mp4",
            "--output", output_template,
            url
        ]

        cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE")
        if cookies_file and os.path.exists(cookies_file):
            dl_cmd.extend(["--cookies", cookies_file])

        subprocess.run(dl_cmd, check=True)

    def download(self, url: str) -> Dict[str, Any]:
        """
        Télécharge la vidéo au format MP4 optimal (max 1080p pour le traitement 9:16).
        Isole le téléchargement dans un sous-dossier de session unique pour éviter
        toute collision ou fallback vers des fichiers arbitraires non liés.
        """
        url = str(url).strip().strip("'\"").strip()
        print(f"📥 [Media-Bot] Analyse du lien source : {url}")
        video_info = self.get_video_info(url)
        title = video_info.get("title", "video_source")
        video_id = str(video_info.get("id", "source"))
        duration = video_info.get("duration", 0)

        # Création d'un sous-répertoire de session isolé pour éviter tout conflit ou fallback parasite
        session_id = f"session_{video_id}_{uuid.uuid4().hex[:8]}"
        session_dir = os.path.join(self.download_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)

        output_template = os.path.join(session_dir, f"{video_id}_%(title).40s.%(ext)s")

        print(f"🎬 [Media-Bot] Téléchargement de la vidéo : '{title}' (Durée: {duration}s)")
        self._download_video(url, output_template)

        # Identifier les fichiers téléchargés strictement dans le répertoire de session
        video_file = None
        subtitle_file = None

        valid_video_exts = (".mp4", ".mkv", ".webm", ".mov")
        for fname in sorted(os.listdir(session_dir)):
            full_p = os.path.join(session_dir, fname)
            if fname.startswith(video_id) and any(fname.endswith(ext) for ext in valid_video_exts):
                video_file = full_p
            elif any(fname.endswith(ext) for ext in valid_video_exts) and video_file is None:
                video_file = full_p

            if fname.startswith(video_id) and (fname.endswith(".vtt") or fname.endswith(".srt")):
                if "fr" in fname.lower() or not subtitle_file:
                    subtitle_file = full_p
            elif (fname.endswith(".vtt") or fname.endswith(".srt")) and not subtitle_file:
                subtitle_file = full_p

        # Échec strict si aucun fichier vidéo n'a été produit (aucun fallback aléatoire)
        if not video_file or not os.path.exists(video_file):
            raise RuntimeError(
                f"Échec du téléchargement pour {url} : aucun fichier vidéo ({', '.join(valid_video_exts)}) généré pour l'identifiant '{video_id}' dans '{session_dir}'."
            )

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
