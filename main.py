#!/usr/bin/env python3
"""
TikTok Autopilot — Script Principal
Lancé par Karl ou par les workflows automatiques GitHub Actions.
"""

import os
import sys
import argparse
import subprocess
from src.pipeline import TikTokPipeline

def run_synthetic_demo(output_dir: str):
    """
    Crée une vidéo test de 35 secondes avec sous-titres et génère le TikTok final
    pour valider l'ensemble de la chaîne sans nécessiter de téléchargement externe lourd.
    """
    print("🎬 [Mode Démo] Génération d'une vidéo synthétique d'exemple...")
    os.makedirs("downloads", exist_ok=True)
    demo_video = "downloads/demo_source.mp4"
    demo_vtt = "downloads/demo_source.vtt"

    # Générer une vidéo de 35 secondes en 16:9 avec son sinusoïdal doux
    create_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=35:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=35",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        demo_video
    ]
    subprocess.run(create_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Générer des sous-titres de test avec des mots viraux
    vtt_content = """WEBVTT

00:00:00.500 --> 00:00:04.000
Voici le grand secret que 99% des créateurs ignorent.

00:00:04.500 --> 00:00:09.000
L'erreur fatale est de passer des heures sur du montage manuel.

00:00:09.500 --> 00:00:15.000
En réalité, la clé de la réussite sur TikTok, c'est la régularité et les accroches.

00:00:15.500 --> 00:00:22.000
Si tu automatises la découpe des punchlines, ton business passe au niveau supérieur.

00:00:22.500 --> 00:00:28.000
Voici exactement la méthode pour captiver l'attention dès les trois premières secondes.

00:00:28.500 --> 00:00:34.000
Abonne-toi maintenant et passe à l'action dès aujourd'hui.
"""
    with open(demo_vtt, "w", encoding="utf-8") as f:
        f.write(vtt_content)

    pipeline = TikTokPipeline(output_dir=output_dir, temp_dir="downloads")
    result = pipeline._process_video_file(
        video_path=demo_video,
        video_title="Demo Masterclass Business Karl",
        subtitle_path=demo_vtt,
        top_k=1
    )
    print("\n✅ [Mode Démo] Démonstration réussie à 100% !")
    return result

def main():
    parser = argparse.ArgumentParser(description="TikTok Autopilot — Usine automatisée de clips TikTok pour Karl")
    parser.add_argument("--url", type=str, help="Lien de la vidéo source (YouTube, podcast...)")
    parser.add_argument("--video", type=str, help="Chemin d'une vidéo locale MP4")
    parser.add_argument("--clips", type=int, default=1, help="Nombre de clips TikTok à générer (défaut: 1)")
    parser.add_argument("--output", type=str, default="output", help="Dossier de sortie des vidéos TikTok")
    parser.add_argument("--demo", action="store_true", help="Lancer un test complet avec une vidéo de démo")

    args = parser.parse_args()

    if args.demo:
        run_synthetic_demo(args.output)
        return

    if not args.url and not args.video:
        print("💡 Astuce Karl : Lance la démo avec '--demo' ou fournis un lien avec '--url <lien>'")
        parser.print_help()
        sys.exit(1)

    pipeline = TikTokPipeline(output_dir=args.output)

    if args.url:
        pipeline.process_url(args.url, top_k=args.clips)
    elif args.video:
        pipeline.process_local_file(args.video, top_k=args.clips)

if __name__ == "__main__":
    main()
