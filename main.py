#!/usr/bin/env python3
"""
TikTok Autopilot — Script Principal
Lancé par Karl ou par les workflows automatiques GitHub Actions.
Prend en charge les thèmes personnalisés, le branding Karl Studio,
la barre de progression dynamique et le traitement par lot.
"""

import os
import sys
import argparse
import subprocess
from src.pipeline import TikTokPipeline

def run_synthetic_demo(output_dir: str, theme: str = "gold", watermark: str = "@karlstudio"):
    """
    Crée une vidéo test de 35 secondes avec sous-titres et génère le TikTok final
    pour valider l'ensemble de la chaîne avec les nouveaux habillages graphiques.
    """
    print(f"🎬 [Mode Démo] Génération d'un exemple TikTok (Thème: {theme}, Watermark: {watermark})...")
    os.makedirs("downloads", exist_ok=True)
    demo_video = "downloads/demo_source.mp4"
    demo_vtt = "downloads/demo_source.vtt"

    create_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=35:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=35",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        demo_video
    ]
    subprocess.run(create_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

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
Abonne-toi maintenant et découvre Karl Studio dès aujourd'hui.
"""
    with open(demo_vtt, "w", encoding="utf-8") as f:
        f.write(vtt_content)

    pipeline = TikTokPipeline(
        output_dir=output_dir,
        temp_dir="downloads",
        theme_name=theme,
        watermark=watermark,
        with_progress_bar=True
    )
    result = pipeline._process_video_file(
        video_path=demo_video,
        video_title="Masterclass Karl Studio",
        subtitle_path=demo_vtt,
        top_k=1
    )
    print("\n✅ [Mode Démo] Démonstration réussie avec succès !")
    return result

def main():
    parser = argparse.ArgumentParser(description="TikTok Autopilot — Usine automatisée de clips TikTok pour Karl")
    parser.add_argument("--url", type=str, help="Lien de la vidéo source (YouTube, prédication, émission...)")
    parser.add_argument("--video", type=str, help="Chemin d'une vidéo locale MP4")
    parser.add_argument("--batch", type=str, help="Fichier texte contenant plusieurs liens (1 par ligne)")
    parser.add_argument("--clips", type=int, default=1, help="Nombre de clips TikTok à extraire par vidéo (défaut: 1)")
    parser.add_argument("--output", type=str, default="output", help="Dossier de sortie des vidéos TikTok")
    parser.add_argument("--theme", type=str, default="gospel", choices=["gospel", "gold", "neon", "minimal"], help="Thème visuel (gospel, gold, neon, minimal)")
    parser.add_argument("--watermark", type=str, default="@parole.de.foi", help="Badge / Watermark dans la Safe Zone")
    parser.add_argument("--publish", type=str, default="draft", choices=["none", "draft", "public"], help="Mode de publication TikTok (none, draft=Brouillon privé, public=Publication directe)")
    parser.add_argument("--no-progress-bar", action="store_true", help="Désactiver la barre de progression en bas")
    parser.add_argument("--webhook", type=str, help="URL de notification Webhook Discord ou Telegram")
    parser.add_argument("--demo", action="store_true", help="Lancer un test complet avec une vidéo de démo")

    args = parser.parse_args()

    if args.demo:
        run_synthetic_demo(args.output, theme=args.theme, watermark=args.watermark)
        return

    if not args.url and not args.video and not args.batch:
        print("💡 Astuce Karl : Lance la démo avec '--demo' ou fournis un lien de prédication avec '--url <lien>'")
        parser.print_help()
        sys.exit(1)

    pipeline = TikTokPipeline(
        output_dir=args.output,
        theme_name=args.theme,
        watermark=args.watermark,
        with_progress_bar=not args.no_progress_bar,
        webhook_url=args.webhook,
        publish_mode=args.publish
    )

    if args.batch:
        if not os.path.exists(args.batch):
            print(f"❌ Fichier batch introuvable : {args.batch}")
            sys.exit(1)
        with open(args.batch, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        pipeline.process_batch(urls, top_k=args.clips)
    elif args.url:
        clean_url = args.url.strip().strip("'\"").strip()
        pipeline.process_url(clean_url, top_k=args.clips)
    elif args.video:
        pipeline.process_local_file(args.video, top_k=args.clips)

if __name__ == "__main__":
    main()
