import os
import sys
import json
import uuid
import subprocess
from typing import Dict, Any, Optional, List, Tuple


class VideoDownloader:
    """
    Sous-agent Media-Bot / Composant de téléchargement.
    Gère la récupération de vidéos sources (YouTube, podcasts, web) via yt-dlp.
    Extrait les sous-titres natifs pour gagner un temps précieux (0.5s vs plusieurs minutes).
    """

    YOUTUBE_STRATEGIES: List[Tuple[str, List[str]]] = [
        (
            "tv,web_embedded",
            [
                "--js-runtimes", "node",
                "--remote-components", "ejs:github",
                "--extractor-args", "youtube:player_client=tv,web_embedded;player_skip=webpage",
            ],
        ),
        (
            "ipv4+default_ejs",
            [
                "--force-ipv4",
                "--js-runtimes", "node",
                "--remote-components", "ejs:github",
            ],
        ),
        (
            "ipv4+android_sdkless,mweb",
            [
                "--force-ipv4",
                "--js-runtimes", "node",
                "--remote-components", "ejs:github",
                "--extractor-args", "youtube:player_client=android_sdkless,mweb",
            ],
        ),
        (
            "ipv4+android_vr",
            [
                "--force-ipv4",
                "--extractor-args", "youtube:player_client=android_vr",
            ],
        ),
    ]

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    @staticmethod
    def _is_youtube_url(url: str) -> bool:
        lower = url.lower()
        return "youtube.com" in lower or "youtu.be" in lower

    @staticmethod
    def _cleanup_partial_downloads(output_template: str) -> None:
        session_dir = os.path.dirname(output_template)
        if not session_dir or not os.path.isdir(session_dir):
            return
        for fname in os.listdir(session_dir):
            if fname.endswith((".part", ".ytdl")):
                try:
                    os.remove(os.path.join(session_dir, fname))
                except OSError:
                    pass

    def resolve_video_url(self, url: str) -> str:
        """
        Si l'URL fournie est une playlist ou une bibliothèque YouTube,
        extrait automatiquement la vidéo active (ou la 1ère vidéo de la bibliothèque).
        """
        clean_url = str(url).strip().strip("'\"").strip()
        if "playlist?list=" in clean_url or "&list=" in clean_url:
            print(f"📋 [Media-Bot] Bibliothèque / Playlist détectée : {clean_url}")
            cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE")
            playlist_flags_list = [
                [],
                ["--force-ipv4"],
                ["--force-ipv4", "--extractor-args", "youtube:player_client=android_vr"],
            ]
            for extra_flags in playlist_flags_list:
                try:
                    cmd = [
                        sys.executable, "-m", "yt_dlp",
                        *extra_flags,
                        "--flat-playlist",
                        "--dump-json",
                        clean_url
                    ]
                    if cookies_file and os.path.exists(cookies_file):
                        cmd.extend(["--cookies", cookies_file])
                    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    lines = [l for l in res.stdout.strip().split("\n") if l.strip()]
                    if lines:
                        first_item = json.loads(lines[0])
                        video_id = first_item.get("id")
                        if video_id:
                            resolved = f"https://www.youtube.com/watch?v={video_id}"
                            print(f"🎬 [Media-Bot] Prédication sélectionnée : '{first_item.get('title')}' ({resolved})")
                            return resolved
                except Exception as e_pl:
                    print(f"⚠️ Note playlist : {e_pl}")
        return clean_url

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extrait les métadonnées de la vidéo via yt-dlp sans la télécharger.
        Invoque [sys.executable, "-m", "yt_dlp", ...] pour garantir l'utilisation
        du paquet dans l'environnement virtuel actif.
        """
        url = self.resolve_video_url(url)
        cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE")
        strategies = self.YOUTUBE_STRATEGIES if self._is_youtube_url(url) else [self.YOUTUBE_STRATEGIES[0]]

        last_error: Optional[Exception] = None
        for strategy_name, extra_args in strategies:
            info_cmd = [
                sys.executable, "-m", "yt_dlp",
                *extra_args,
                "--dump-json",
                "--no-playlist",
                url
            ]
            if cookies_file and os.path.exists(cookies_file):
                info_cmd.extend(["--cookies", cookies_file])

            try:
                result = subprocess.run(info_cmd, capture_output=True, text=True, check=True)
                raw_out = result.stdout.strip()
                first_json_line = raw_out.splitlines()[0] if raw_out else raw_out
                return json.loads(first_json_line)
            except Exception as e:
                last_error = e
                print(f"⚠️ [Media-Bot] Métadonnées ({strategy_name}) échouées : {e}")

        print(f"⚠️ Impossible d'extraire les infos détaillées via yt-dlp: {last_error}")
        return {
            "title": "video_source",
            "id": "source",
            "duration": 0
        }

    def _download_video(self, url: str, output_template: str) -> None:
        """
        Télécharge le flux vidéo MP4 et les sous-titres via yt-dlp.
        Utilise [sys.executable, "-m", "yt_dlp", ...] pour la résilience de l'interpréteur,
        avec bascule automatique entre clients YouTube en cas de blocage bot-check IP.
        """
        url = str(url).strip().strip("'\"").strip()
        cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE")
        strategies = self.YOUTUBE_STRATEGIES if self._is_youtube_url(url) else [self.YOUTUBE_STRATEGIES[0]]
        last_error: Optional[subprocess.CalledProcessError] = None

        # Passe 1 : Vidéo + sous-titres natifs français (gain de temps majeur vs Whisper)
        for strategy_name, extra_args in strategies:
            dl_cmd = [
                sys.executable, "-m", "yt_dlp",
                *extra_args,
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
            if cookies_file and os.path.exists(cookies_file):
                dl_cmd.extend(["--cookies", cookies_file])

            try:
                subprocess.run(dl_cmd, check=True)
                return
            except subprocess.CalledProcessError as e:
                last_error = e
                self._cleanup_partial_downloads(output_template)
                print(f"⚠️ [Media-Bot] Échec téléchargement + sous-titres ({strategy_name}) : {e}")

        # Passe 2 : Vidéo seule (sans sous-titres) si le téléchargement des sous-titres échoue
        print(f"⚠️ Note sous-titres YouTube ({last_error}) : téléchargement direct du flux vidéo seul pour transcription locale...")
        for strategy_name, extra_args in strategies:
            fallback_cmd = [
                sys.executable, "-m", "yt_dlp",
                *extra_args,
                "--format", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "--no-playlist",
                "--merge-output-format", "mp4",
                "--output", output_template,
                url
            ]
            if cookies_file and os.path.exists(cookies_file):
                fallback_cmd.extend(["--cookies", cookies_file])

            try:
                subprocess.run(fallback_cmd, check=True)
                return
            except subprocess.CalledProcessError as e:
                last_error = e
                self._cleanup_partial_downloads(output_template)
                print(f"⚠️ [Media-Bot] Échec flux direct ({strategy_name}) : {e}")

        if last_error is not None:
            raise last_error

    def download(self, url: str) -> Dict[str, Any]:
        """
        Télécharge la vidéo au format MP4 optimal (max 1080p pour le traitement 9:16).
        Isole le téléchargement dans un sous-dossier de session unique pour éviter
        toute collision ou fallback vers des fichiers arbitraires non liés.
        """
        url = self.resolve_video_url(url)
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
