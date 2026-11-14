import os
import sys
import json
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

try:
    from .pipeline import TikTokPipeline
    from .gospel_intelligence import GospelIntelligence
except ImportError:
    from pipeline import TikTokPipeline
    from gospel_intelligence import GospelIntelligence

DEFAULT_PLAYLIST_URL = "https://youtube.com/playlist?list=PLeK7sB4DCSgs&si=jnf4lYNDP9huFSvJ"
HISTORY_FILE = os.path.join("history", "processed_videos.json")
REPORT_FILE = os.path.join("history", "LAST_AUTOPILOT_REPORT.md")


class LibraryAutopilot:
    """
    Système Autonome 24/7 de Traitement de la Bibliothèque de Prédications de Karl.
    - Accès direct et autonome au dossier/playlist YouTube de Karl.
    - Détecte automatiquement la prochaine prédication non encore traitée.
    - Fait tourner le sous-agent 'Gospel Intelligence' pour extraire les 10 meilleurs
      segments de 1 à 2 min (60s à 120s) calibrés pour les vérités bibliques et de vie.
    - Met en forme en 9:16 vertical (Thème Gospel Gold + Sous-titres dynamiques + Safe-Zone).
    - Dépose directement les 10 vidéos dans les Brouillons de TikTok Studio pour vérification par Karl.
    - Mémorise l'historique dans history/processed_videos.json pour ne jamais retraiter la même vidéo.
    """

    def __init__(
        self,
        playlist_url: str = DEFAULT_PLAYLIST_URL,
        history_path: str = HISTORY_FILE,
        report_path: str = REPORT_FILE,
        output_dir: str = "output",
        theme: str = "gospel",
        watermark: str = "@parole.de.foi",
        publish_mode: str = "draft",
        clips_count: int = 10
    ):
        self.playlist_url = playlist_url
        self.history_path = history_path
        self.report_path = report_path
        self.output_dir = output_dir
        self.theme = theme
        self.watermark = watermark
        self.publish_mode = publish_mode
        self.clips_count = clips_count

        os.makedirs(os.path.dirname(self.history_path) or ".", exist_ok=True)
        self.history_data = self._load_history()

    def _load_history(self) -> Dict[str, Any]:
        """Charge l'historique des vidéos traitées."""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Erreur lecture historique ({e}), réinitialisation...")
        return {
            "playlist_url": self.playlist_url,
            "playlist_title": "Shorts à Générer",
            "last_updated": None,
            "total_processed": 0,
            "processed_video_ids": [],
            "history": []
        }

    def _save_history(self) -> None:
        """Sauvegarde atomique du registre d'historique."""
        os.makedirs(os.path.dirname(self.history_path) or ".", exist_ok=True)
        self.history_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.history_data["total_processed"] = len(self.history_data.get("processed_video_ids", []))
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(self.history_data, f, indent=2, ensure_ascii=False)
        print(f"💾 [Autopilot] Registre mis à jour : {len(self.history_data['processed_video_ids'])} vidéo(s) enregistrée(s).")

    def fetch_playlist_items(self) -> List[Dict[str, Any]]:
        """
        Interroge la bibliothèque YouTube pour récupérer la liste ordonnée des prédications.
        Utilise yt-dlp avec contournement anti-datacenter.
        """
        print(f"📡 [Autopilot 24/7] Analyse de la bibliothèque YouTube : {self.playlist_url}")
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            "--extractor-args", "youtube:player_client=tv,web_embedded;player_skip=webpage",
            "--flat-playlist",
            "--dump-json",
            self.playlist_url
        ]

        cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE")
        if cookies_file and os.path.exists(cookies_file):
            cmd.extend(["--cookies", cookies_file])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            items = []
            for line in res.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    v_id = data.get("id")
                    if v_id:
                        items.append({
                            "id": v_id,
                            "title": data.get("title", f"Vidéo {v_id}"),
                            "duration": data.get("duration", 0),
                            "duration_string": data.get("duration_string", "Inconnue"),
                            "url": f"https://www.youtube.com/watch?v={v_id}",
                            "uploader": data.get("uploader", "Prédicateur")
                        })
                except json.JSONDecodeError:
                    continue
            print(f"✅ [Autopilot] {len(items)} prédication(s) répertoriée(s) dans la bibliothèque de Karl.")
            return items
        except Exception as e:
            print(f"❌ [Autopilot] Erreur lors de la lecture de la bibliothèque YouTube : {e}")
            return []

    def get_unprocessed_videos(self) -> List[Dict[str, Any]]:
        """Filtre les prédications pour ne conserver que celles pas encore traitées."""
        all_items = self.fetch_playlist_items()
        processed_ids = set(self.history_data.get("processed_video_ids", []))
        unprocessed = [v for v in all_items if v["id"] not in processed_ids]
        print(f"📊 [Autopilot] Bilan bibliothèque : {len(unprocessed)} en attente / {len(all_items)} total.")
        return unprocessed

    def generate_markdown_report(self, status: str, last_video: Optional[Dict[str, Any]] = None, clips_info: Optional[List[Dict[str, Any]]] = None) -> None:
        """Génère un rapport lisible pour Karl visible directement sur GitHub."""
        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M GMT")
        total_p = len(self.history_data.get("processed_video_ids", []))

        lines = [
            "# 🕊️ Rapport Autopilot 24/7 - Prédications & Brouillons TikTok",
            f"**Dernière exécution :** {now_str} (Fuseau horaire GMT / Abidjan)",
            f"**Statut :** `{status}`",
            f"**Total prédications traitées :** {total_p}",
            f"**Bibliothèque source :** [Accéder au dossier YouTube]({self.playlist_url})",
            "",
            "---",
            ""
        ]

        if last_video and clips_info:
            lines.extend([
                "## 🎬 Dernière Prédication Traitée",
                f"- **Titre :** {last_video.get('title')}",
                f"- **Lien :** [{last_video.get('url')}]({last_video.get('url')})",
                f"- **Durée source :** {last_video.get('duration_string', str(last_video.get('duration', '')) + 's')}",
                f"- **Clips extraits (1 à 2 min) :** {len(clips_info)}",
                "- **Destination :** Brouillons TikTok Studio 📱",
                "",
                f"### 📋 Liste des {len(clips_info)} Shorts Générés avec Gospel Intelligence",
                "| # | Durée | Accroche (Hook) | Cible Rétention | Brouillon TikTok |",
                "|---|---|---|---|---|"
            ])

            for c in clips_info:
                pub = c.get("publication") or {}
                pub_status = pub.get("status", "prêt")
                if pub_status == "success":
                    badge = "✅ Publié sur TikTok" if self.publish_mode == "public" else "✅ Déposé dans Brouillons"
                elif pub_status == "completed_with_screenshots":
                    badge = "📸 Envoyé (Vérifier captures)"
                elif pub_status == "auth_error":
                    badge = "🔑 Session à renouveler (TIKTOK_SESSION_ID)"
                elif pub_status in ("error", "dom_error"):
                    badge = "⚠️ Échec transfert (Vidéo prête en ZIP)"
                elif pub_status == "ready_to_publish":
                    badge = "📁 Fichier Prêt (Clé TikTok requise)"
                else:
                    badge = "📁 Fichier Prêt (Archive ZIP)"
                lines.append(
                    f"| Clip {c.get('clip_number')} | {int(c.get('duration', 0))}s | **{c.get('hook')}** | {c.get('retention', '85%')} | {badge} |"
                )

            if status == "EN_ATTENTE_SESSION":
                lines.extend([
                    "",
                    "### 🔑 Action requise pour déposer automatiquement dans tes Brouillons TikTok",
                    "Les vidéos et fiches textes ont bien été générées et archivées dans GitHub Actions, mais TikTok a demandé une reconnexion.",
                    "1. Connecte-toi à **TikTok Studio** dans Chrome/Edge, ouvre **Cookie-Editor** et clique sur **Export > Export as JSON**.",
                    "2. Colle ce texte JSON dans le Secret GitHub `TIKTOK_SESSION_ID` (Paramètres > Secrets > Actions).",
                    "3. Cette prédication n'est **pas marquée comme terminée** : le robot réessaiera automatiquement au prochain cycle !",
                    ""
                ])
            elif status.startswith("ECHEC"):
                lines.extend([
                    "",
                    "### 💡 Récupération & Vérification pour Karl",
                    "Les vidéos montées et leurs fiches textes restent téléchargeables immédiatement dans l'archive `tiktok-brouillons-autopilot` de cette exécution GitHub Actions.",
                    "La prédication sera automatiquement retentée lors du prochain cycle.",
                    ""
                ])
            else:
                lines.extend([
                    "",
                    "### 💡 Prochaine Étape pour Karl",
                    "1. Ouvre ton application TikTok sur ton téléphone.",
                    "2. Rends-toi dans ton profil > **Brouillons**.",
                    "3. Les vidéos y sont déjà pré-remplies avec l'accroche, les hashtags (#mariage, #foi, #chretien) et le texte.",
                    "4. Clique sur 'Publier' au moment où tu le souhaites !",
                    ""
                ])
        else:
            lines.extend([
                "## ℹ️ État de la Bibliothèque",
                "Toutes les prédications actuellement présentes dans la bibliothèque de Karl ont déjà été découpées et transférées.",
                "Dès que Karl ajoute une nouvelle prédication dans la playlist YouTube, l'Autopilot la traitera automatiquement lors du prochain cycle 24/7 !",
                ""
            ])

        lines.extend([
            "---",
            "*Généré automatiquement par le CEO Multi-Agents (DevOps-Bot, Media-Bot, Growth-Bot & Gospel Intelligence)*"
        ])

        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"📄 [Autopilot] Rapport enregistré : {self.report_path}")

    def run_cycle(self, force_video_id: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Exécute un cycle de production autonome.
        1. Identifie la cible (soit l'ID forcé, soit la première vidéo non traitée).
        2. Lance le pipeline complet (clips de 1-2 min + Thème Gospel + Dépôt brouillon).
        3. Enregistre l'historique (uniquement en cas de livraison effective) et génère le rapport.
        """
        print(f"\n========================================================")
        print(f"👑 [CEO Autopilot] Lancement du cycle autonome 24/7")
        print(f"Heure : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Bibliothèque : {self.playlist_url}")
        print(f"Mode : {'DRY-RUN (Test sans rendu)' if dry_run else 'PRODUCTION ACTIVE'}")
        print(f"========================================================\n")

        all_items = self.fetch_playlist_items()
        if not all_items:
            print("⚠️ Impossible d'accéder aux éléments de la bibliothèque. Vérifiez la connexion ou le lien.")
            return {"status": "error", "message": "Bibliothèque inaccessible"}

        target_video = None

        if force_video_id:
            for item in all_items:
                if item["id"] == force_video_id:
                    target_video = item
                    break
            if not target_video:
                print(f"⚠️ Vidéo forcée {force_video_id} introuvable dans la playlist, utilisation directe du lien.")
                target_video = {
                    "id": force_video_id,
                    "title": f"Prédication {force_video_id}",
                    "url": f"https://www.youtube.com/watch?v={force_video_id}",
                    "duration": 0
                }
        else:
            processed_ids = set(self.history_data.get("processed_video_ids", []))
            for item in all_items:
                if item["id"] not in processed_ids:
                    target_video = item
                    break

        if not target_video:
            print("🎉 [CEO Autopilot] Toutes les prédications de la bibliothèque sont déjà traitées !")
            print("Le système reste en veille active pour toute nouvelle vidéo ajoutée par Karl.")
            self.generate_markdown_report(status="TOUTES_VIDEOS_TRAITEES")
            return {
                "status": "up_to_date",
                "message": "Toutes les prédications ont déjà été traitées."
            }

        print(f"🎯 [CEO Autopilot] Prédication sélectionnée pour ce cycle :")
        print(f"• Titre : {target_video['title']}")
        print(f"• URL : {target_video['url']}")
        print(f"• Identifiant : {target_video['id']}")

        if dry_run:
            print("🔍 Mode DRY-RUN : Simulation réussie. Aucune vidéo n'a été téléchargée.")
            return {
                "status": "dry_run",
                "selected_video": target_video
            }

        # Lancement du Pipeline de Production
        pipeline = TikTokPipeline(
            output_dir=self.output_dir,
            theme_name=self.theme,
            watermark=self.watermark,
            publish_mode=self.publish_mode,
            with_progress_bar=True
        )

        try:
            results = pipeline.process_url(target_video["url"], top_k=self.clips_count)
            clips = results.get("clips", [])

            statuses = [(c.get("publication") or {}).get("status", "ready") for c in clips]
            delivered_count = sum(1 for st in statuses if st == "success")
            has_auth_error = any(st in ("auth_error", "ready_to_publish") for st in statuses)

            if self.publish_mode == "none":
                cycle_success = len(clips) > 0
                report_status = "SUCCES" if cycle_success else "ERREUR"
            else:
                cycle_success = delivered_count > 0
                if delivered_count > 0 and delivered_count == len(clips):
                    report_status = "SUCCES"
                elif delivered_count > 0:
                    report_status = f"SUCCES_PARTIEL ({delivered_count}/{len(clips)})"
                elif has_auth_error:
                    report_status = "EN_ATTENTE_SESSION"
                else:
                    report_status = "ECHEC_ENVOI_TIKTOK"

            # N'enregistrer la vidéo comme terminée que si le transfert (ou génération locale si publish=none) a réussi
            v_id = target_video["id"]
            if cycle_success:
                if v_id not in self.history_data["processed_video_ids"]:
                    self.history_data["processed_video_ids"].append(v_id)
            else:
                print(
                    f"⚠️ [CEO Autopilot] Vidéo '{v_id}' conservée en file d'attente "
                    f"(statut : {report_status}) — réessai automatique dès que la session TikTok sera valide."
                )

            history_entry = {
                "id": v_id,
                "title": target_video["title"],
                "url": target_video["url"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "delivery_status": report_status,
                "clips_count": len(clips),
                "clips_published": delivered_count,
                "theme": self.theme,
                "watermark": self.watermark,
                "clips_summary": [
                    {
                        "clip_number": c.get("clip_number"),
                        "duration": c.get("duration"),
                        "hook": c.get("hook"),
                        "retention": c.get("retention"),
                        "publication_status": (c.get("publication") or {}).get("status", "ready")
                    }
                    for c in clips
                ]
            }
            self.history_data["history"].append(history_entry)
            self._save_history()

            # Mise à jour du rapport Markdown pour Karl
            self.generate_markdown_report(
                status=report_status,
                last_video=target_video,
                clips_info=clips
            )

            if cycle_success:
                if self.publish_mode == "none":
                    print(f"\n✨ [CEO Autopilot] Cycle terminé ! {len(clips)} clip(s) généré(s) en archive locale.")
                else:
                    print(f"\n✨ [CEO Autopilot] Cycle terminé avec succès ! {delivered_count}/{len(clips)} clip(s) transféré(s) vers TikTok Studio.")
                return {
                    "status": "success",
                    "video": target_video,
                    "clips_generated": len(clips),
                    "clips_published": delivered_count,
                }

            print(f"\n⚠️ [CEO Autopilot] {len(clips)} clip(s) prêt(s) en archive, mais 0 transféré(s) vers TikTok Studio ({report_status}).")
            return {
                "status": "auth_error" if has_auth_error else "publish_failed",
                "video": target_video,
                "clips_generated": len(clips),
                "clips_published": 0,
            }
        except Exception as e:
            print(f"❌ [CEO Autopilot] Échec du cycle de traitement : {e}")
            self.generate_markdown_report(
                status=f"ERREUR : {e}",
                last_video=target_video,
                clips_info=[]
            )
            raise e


def main():
    parser = argparse.ArgumentParser(description="Autopilot 24/7 Bibliothèque YouTube -> Brouillons TikTok Studio")
    parser.add_argument("--playlist", type=str, default=DEFAULT_PLAYLIST_URL, help="URL de la bibliothèque YouTube")
    parser.add_argument("--clips", type=int, default=10, help="Nombre de clips de 1-2 min à extraire")
    parser.add_argument("--theme", type=str, default="gospel", help="Thème visuel (gospel, gold, neon, minimal)")
    parser.add_argument("--watermark", type=str, default="@parole.de.foi", help="Identifiant safe-zone")
    parser.add_argument("--publish", type=str, default="draft", choices=["draft", "public", "none"], help="Mode publication TikTok")
    parser.add_argument("--force-id", type=str, default=None, help="Forcer le traitement d'une vidéo spécifique")
    parser.add_argument("--dry-run", action="store_true", help="Simule la détection sans effectuer le rendu")

    args = parser.parse_args()

    # Prise en charge des variables d'environnement
    force_id = args.force_id or os.environ.get("FORCE_VIDEO_ID")
    publish_mode = os.environ.get("PUBLISH_MODE", args.publish)

    bot = LibraryAutopilot(
        playlist_url=args.playlist,
        theme=args.theme,
        watermark=args.watermark,
        publish_mode=publish_mode,
        clips_count=args.clips
    )

    bot.run_cycle(force_video_id=force_id, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
