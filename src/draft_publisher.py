#!/usr/bin/env python3
"""
Sous-agent DevOps-Bot : Publication directe des Brouillons TikTok Studio existants.
Permet de transformer en publications publiques tous les brouillons déjà présents
dans TikTok Studio (https://www.tiktok.com/tiktokstudio/content?tab=draft).
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional

try:
    from .tiktok_studio_uploader import TikTokStudioUploader
except ImportError:
    from tiktok_studio_uploader import TikTokStudioUploader


def run_publish_drafts(
    max_count: int = 30,
    dry_run: bool = False,
    pause_seconds: float = 3.0,
    screenshots_dir: str = "output/draft_screenshots",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Exécute la publication des brouillons TikTok Studio et sauvegarde un rapport JSON."""
    os.makedirs(screenshots_dir, exist_ok=True)
    uploader = TikTokStudioUploader(session_id=session_id, screenshots_dir=screenshots_dir)
    result = uploader.publish_all_drafts(
        max_count=max_count,
        dry_run=dry_run,
        pause_seconds=pause_seconds,
    )

    report_path = os.path.join(screenshots_dir, "draft_publish_report.json")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"📄 [DevOps-Bot] Rapport détaillé enregistré : {report_path}")
    except Exception as e_rep:
        print(f"⚠️ Impossible d'écrire le rapport JSON ({e_rep})")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Publie les brouillons TikTok Studio en mode public.")
    parser.add_argument("--max", type=int, default=30, help="Nombre maximal de brouillons à publier lors de cette passe")
    parser.add_argument("--dry-run", action="store_true", help="Inspecte et compte les brouillons sans cliquer sur Publier")
    parser.add_argument("--pause", type=float, default=3.0, help="Pause en secondes entre chaque publication")
    parser.add_argument("--screenshots-dir", type=str, default="output/draft_screenshots", help="Dossier de sortie des captures d'écran")

    args = parser.parse_args()
    result = run_publish_drafts(
        max_count=args.max,
        dry_run=args.dry_run,
        pause_seconds=args.pause,
        screenshots_dir=args.screenshots_dir,
    )

    status = result.get("status")
    if status in ("auth_error", "dom_error", "error"):
        print(f"❌ Échec publication des brouillons (statut={status}) : {result.get('error', '')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
