import os
import json
from typing import Dict, Any, Optional

from .downloader import VideoDownloader
from .transcriber import VideoTranscriber
from .clip_extractor import ClipExtractor
from .growth_optimizer import GrowthOptimizer
from .video_formatter import VideoFormatter

class TikTokPipeline:
    """
    L'Orchestrateur Principal de la Machine TikTok.
    Pilote l'action conjointe de DevOps-Bot, Media-Bot et Growth-Bot.
    """

    def __init__(self, output_dir: str = "output", temp_dir: str = "downloads"):
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        self.downloader = VideoDownloader(download_dir=self.temp_dir)
        self.transcriber = VideoTranscriber(model_size="tiny")
        self.extractor = ClipExtractor(min_duration=25.0, max_duration=58.0)
        self.growth = GrowthOptimizer()
        self.formatter = VideoFormatter(output_dir=self.output_dir)

    def process_url(self, url: str, top_k: int = 1) -> Dict[str, Any]:
        """
        Traite un lien vidéo (Option A) de bout en bout.
        """
        print(f"\n========================================================")
        print(f"🚀 [CEO Orchestrateur] Démarrage du pipeline TikTok pour Karl")
        print(f"Lien : {url}")
        print(f"========================================================\n")

        # Étape 1 : Téléchargement de la vidéo & extraction sous-titres
        download_data = self.downloader.download(url)
        video_path = download_data["video_path"]
        subtitle_path = download_data["subtitle_path"]
        video_title = download_data["title"]

        return self._process_video_file(video_path, video_title, subtitle_path, top_k=top_k)

    def process_local_file(self, video_path: str, video_title: Optional[str] = None, top_k: int = 1) -> Dict[str, Any]:
        """
        Traite un fichier vidéo local déjà sur la machine.
        """
        if not video_title:
            video_title = os.path.basename(video_path).rsplit(".", 1)[0]
        return self._process_video_file(video_path, video_title, subtitle_path=None, top_k=top_k)

    def _process_video_file(self, video_path: str, video_title: str, subtitle_path: Optional[str], top_k: int = 1) -> Dict[str, Any]:
        # Étape 2 : Transcription et horodatages (Media-Bot)
        segments = self.transcriber.transcribe(video_path, subtitle_path=subtitle_path)
        if not segments:
            raise ValueError("Impossible d'extraire des segments audio ou sous-titres exploitables.")

        # Étape 3 : Détection des meilleurs extraits (Media-Bot + Growth-Bot)
        best_clips = self.extractor.find_best_clips(segments, top_k=top_k)
        if not best_clips:
            raise ValueError("Aucun extrait pertinent trouvé dans la durée ciblée.")

        generated_clips = []

        for idx, clip in enumerate(best_clips, start=1):
            print(f"\n🎯 [Orchestrateur] Traitement de l'extrait #{idx} (Score: {clip['score']}, Durée: {clip['duration']}s)")

            # Étape 4 : Optimisation virale & Fiche TikTok (Growth-Bot)
            growth_package = self.growth.generate_growth_package(clip, video_title)

            # Étape 5 : Rendu vidéo 9:16 vertical (Media-Bot)
            output_filename = f"tiktok_clip_{idx}_{int(clip['start'])}s.mp4"
            final_video_path = self.formatter.render_tiktok_video(
                video_input=video_path,
                start_time=clip["start"],
                duration=clip["duration"],
                hook_title=growth_package["hook_banner"],
                segments=clip["segments"],
                output_filename=output_filename
            )

            # Étape 6 : Fiche mémo pour Karl
            sheet_filename = f"FICHE_TIKTOK_clip_{idx}.txt"
            sheet_path = os.path.join(self.output_dir, sheet_filename)
            self.growth.export_summary_sheet(growth_package, sheet_path)

            generated_clips.append({
                "clip_number": idx,
                "video_path": final_video_path,
                "sheet_path": sheet_path,
                "hook": growth_package["hook_banner"],
                "caption": growth_package["caption"],
                "hashtags": growth_package["hashtags"],
                "start": clip["start"],
                "end": clip["end"],
                "duration": clip["duration"],
                "retention": growth_package["estimated_retention"]
            })

        # Rapport global
        summary_path = os.path.join(self.output_dir, "tiktok_results.json")
        summary_data = {
            "source_title": video_title,
            "clips_count": len(generated_clips),
            "clips": generated_clips
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        print(f"\n🎉 [CEO Orchestrateur] Pipeline terminé ! {len(generated_clips)} vidéo(s) prêtes dans '{self.output_dir}'")
        return summary_data
