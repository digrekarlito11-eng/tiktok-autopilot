import os
import json
import shutil
import hashlib
import logging
from typing import Dict, Any, Optional, List

from .downloader import VideoDownloader
from .transcriber import VideoTranscriber
from .clip_extractor import ClipExtractor
from .growth_optimizer import GrowthOptimizer
from .video_formatter import VideoFormatter
from .notifier import TikTokNotifier
from .tiktok_publisher import TikTokPublisher

logger = logging.getLogger(__name__)


class TikTokPipeline:
    """
    L'Orchestrateur Principal de la Machine TikTok.
    Pilote l'action conjointe de DevOps-Bot, Media-Bot et Growth-Bot.
    Gère le téléchargement, le découpage, le branding, les fiches de publication
    et la publication directe sur TikTok.
    """

    def __init__(
        self,
        output_dir: str = "output",
        temp_dir: str = "downloads",
        theme_name: str = "gospel",
        watermark: str = "@parole.de.foi",
        with_progress_bar: bool = True,
        webhook_url: Optional[str] = None,
        publish_mode: str = "draft"  # "none", "draft", "public"
    ):
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        self.theme_name = theme_name
        self.watermark = watermark
        self.with_progress_bar = with_progress_bar
        self.publish_mode = (publish_mode or "draft").strip() or "draft"

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        self.downloader = VideoDownloader(download_dir=self.temp_dir)
        self.transcriber = VideoTranscriber(model_size="tiny")
        self.extractor = ClipExtractor(min_duration=60.0, max_duration=120.0)
        self.growth = GrowthOptimizer()
        self.formatter = VideoFormatter(output_dir=self.output_dir)
        self.notifier = TikTokNotifier(webhook_url=webhook_url)
        self.publisher = TikTokPublisher()

    @staticmethod
    def _build_safe_title(video_title: str, video_id: Optional[str] = None) -> str:
        """
        Génère un préfixe de fichier sûr et déterministe, sans collision pour les titres longs
        partageant les 20 premiers caractères (ex: Parties 1, 2, 3 d'une même série).
        """
        raw_clean = "".join(c for c in (video_title or "") if c.isalnum() or c in (" ", "_", "-")).strip()
        prefix = raw_clean[:20].strip()
        if not prefix:
            prefix = "video"
        if len(raw_clean) > 20 or video_id:
            hash_input = f"{video_title}::{video_id or ''}".encode("utf-8")
            short_hash = hashlib.sha1(hash_input).hexdigest()[:6]
            return f"{prefix}_{short_hash}"
        return prefix

    def _cleanup_session_dir(self, video_path: str) -> None:
        """Supprime le sous-dossier temporaire downloads/session_* après traitement."""
        if not video_path:
            return
        parent_dir = os.path.dirname(os.path.abspath(video_path))
        base_name = os.path.basename(parent_dir)
        if base_name.startswith("session_") and os.path.isdir(parent_dir):
            try:
                shutil.rmtree(parent_dir, ignore_errors=True)
                logger.info("🧹 Dossier de session temporaire nettoyé : %s", parent_dir)
            except OSError:
                pass

    def process_url(self, url: str, top_k: int = 10) -> Dict[str, Any]:
        """
        Traite un lien vidéo (Option A) de bout en bout.
        """
        print(f"\n========================================================")
        print(f"🚀 [CEO Orchestrateur] Démarrage du pipeline TikTok pour Karl")
        print(f"Lien : {url}")
        print(f"Thème : {self.theme_name} | Watermark : {self.watermark}")
        print(f"========================================================\n")

        download_data = self.downloader.download(url)
        video_path = download_data["video_path"]
        subtitle_path = download_data.get("subtitle_path")
        video_title = download_data.get("title", "video_source")

        try:
            return self._process_video_file(video_path, video_title, subtitle_path, top_k=top_k)
        finally:
            self._cleanup_session_dir(video_path)

    def process_batch(self, urls: List[str], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Traite une série de vidéos en rafale pour préparer le stock de contenu TikTok de Karl.
        """
        results = []
        all_clips = []
        print(f"\n⚡ [CEO Orchestrateur] Lancement du traitement par lot ({len(urls)} vidéos sources)...")
        for idx, u in enumerate(urls, start=1):
            u_clean = u.strip()
            if not u_clean or u_clean.startswith("#"):
                continue
            print(f"\n--- Traitement {idx}/{len(urls)} : {u_clean} ---")
            try:
                res = self.process_url(u_clean, top_k=top_k)
                results.append(res)
                all_clips.extend(res.get("clips", []))
            except Exception as e:
                print(f"❌ Erreur sur la vidéo {u_clean} : {e}")

        if len(results) > 1:
            summary_path = os.path.join(self.output_dir, "tiktok_results.json")
            batch_summary = {
                "source_title": results[-1].get("source_title", "Batch TikTok"),
                "clips_count": len(all_clips),
                "theme": self.theme_name,
                "watermark": self.watermark,
                "clips": all_clips,
                "batch_results": results,
            }
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(batch_summary, f, indent=2, ensure_ascii=False)

        return results

    def process_local_file(self, video_path: str, video_title: Optional[str] = None, top_k: int = 10) -> Dict[str, Any]:
        """
        Traite un fichier vidéo local déjà sur la machine.
        """
        if not video_title:
            video_title = os.path.basename(video_path).rsplit(".", 1)[0]
        return self._process_video_file(video_path, video_title, subtitle_path=None, top_k=top_k)

    def _process_video_file(
        self,
        video_path: str,
        video_title: str,
        subtitle_path: Optional[str],
        top_k: int = 10
    ) -> Dict[str, Any]:
        # Étape 2 : Transcription et horodatages (Media-Bot)
        segments = self.transcriber.transcribe(video_path, subtitle_path=subtitle_path)
        if not segments:
            raise ValueError("Impossible d'extraire des segments audio ou sous-titres exploitables.")

        # Étape 3 : Détection des meilleurs extraits (Media-Bot + Growth-Bot)
        best_clips = self.extractor.find_best_clips(segments, top_k=top_k)
        if not best_clips:
            raise ValueError("Aucun extrait pertinent trouvé dans la durée ciblée.")

        generated_clips = []
        safe_title = self._build_safe_title(video_title)

        for idx, clip in enumerate(best_clips, start=1):
            print(f"\n🎯 [Orchestrateur] Traitement de l'extrait #{idx} (Score: {clip['score']}, Durée: {clip['duration']}s)")

            # Étape 4 : Optimisation virale & Fiche TikTok (Growth-Bot)
            growth_package = self.growth.generate_growth_package(clip, video_title)

            # Étape 5 : Rendu vidéo 9:16 vertical (Media-Bot) avec Branding et Barre de progression
            output_filename = f"tiktok_{safe_title}_clip_{idx}_{int(clip['start'])}s.mp4"

            final_video_path = self.formatter.render_tiktok_video(
                video_input=video_path,
                start_time=clip["start"],
                duration=clip["duration"],
                hook_title=growth_package["hook_banner"],
                segments=clip["segments"],
                output_filename=output_filename,
                watermark=self.watermark,
                theme_name=self.theme_name,
                with_progress_bar=self.with_progress_bar
            )

            # Étape 6 : Fiche mémo pour Karl
            sheet_filename = f"FICHE_TIKTOK_{safe_title}_clip_{idx}.txt"
            sheet_path = os.path.join(self.output_dir, sheet_filename)
            self.growth.export_summary_sheet(growth_package, sheet_path)

            # Étape 7 : Publication directe ou mise en brouillon TikTok (DevOps-Bot & Publisher)
            pub_result = None
            if self.publish_mode != "none":
                privacy = "PUBLIC_TO_EVERYONE" if self.publish_mode == "public" else "SELF_ONLY"
                pub_result = self.publisher.publish_clip(
                    video_path=final_video_path,
                    growth_package=growth_package,
                    privacy_level=privacy
                )

            clip_info = {
                "clip_number": idx,
                "video_path": final_video_path,
                "sheet_path": sheet_path,
                "hook": growth_package["hook_banner"],
                "caption": growth_package["caption"],
                "hashtags": growth_package["hashtags"],
                "start": clip["start"],
                "end": clip["end"],
                "duration": clip["duration"],
                "retention": growth_package["estimated_retention"],
                "theme": self.theme_name,
                "watermark": self.watermark,
                "publication": pub_result
            }

            generated_clips.append(clip_info)

            # Étape 8 : Notification automatique (DevOps-Bot)
            self.notifier.notify_clip_ready(clip_info, total_clips=len(best_clips))

        # Rapport global
        summary_path = os.path.join(self.output_dir, "tiktok_results.json")
        summary_data = {
            "source_title": video_title,
            "clips_count": len(generated_clips),
            "theme": self.theme_name,
            "watermark": self.watermark,
            "clips": generated_clips
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        print(f"\n🎉 [CEO Orchestrateur] Pipeline terminé ! {len(generated_clips)} vidéo(s) prêtes dans '{self.output_dir}'")
        return summary_data
