import json
import re
from typing import Dict, Any, List

class GrowthOptimizer:
    """
    Sous-agent Growth-Bot / Spécialiste TikTok Viralité & Monétisation.
    Prend l'extrait sélectionné et produit les éléments indispensables pour l'algorithme TikTok :
    1. Hook visuel pour la bannière du haut (accroche immédiate des 3 secondes).
    2. Description optimisée (SEO TikTok + Appel à l'action).
    3. Hashtags ciblés et tendances.
    """

    def __init__(self):
        pass

    def generate_growth_package(self, clip_info: Dict[str, Any], video_title: str) -> Dict[str, Any]:
        text = clip_info.get("text", "")
        first_sentence = clip_info.get("first_sentence", "")

        # 1. Détermination du Hook pour le bandeau supérieur de la vidéo
        hook_banner = self._generate_hook_banner(first_sentence, text)

        # 2. Génération de la description TikTok (Caption)
        caption = self._generate_caption(text, video_title)

        # 3. Sélection des hashtags performants
        hashtags = self._select_hashtags(text)

        # 4. Score de rétention prévisionnel
        estimated_retention = min(88, int(60 + clip_info.get("score", 10) * 1.5))

        package = {
            "hook_banner": hook_banner,
            "caption": caption,
            "hashtags": hashtags,
            "full_post_text": f"{caption}\n\n{' '.join(hashtags)}",
            "estimated_retention": f"{estimated_retention}%",
            "recommended_audio": "Son tendance ou voix originale avec boost de volume",
            "cta": "Partage à un ami qui a besoin d'entendre ça 💡"
        }

        return package

    def _generate_hook_banner(self, first_sentence: str, full_text: str) -> str:
        """Produit une phrase choc courte en majuscules pour le bandeau du haut."""
        text_lower = (first_sentence + " " + full_text).lower()

        if "secret" in text_lower or "vérité" in text_lower:
            return "LE SECRET QUE PERSONNE NE DIT 🤫"
        elif "erreur" in text_lower or "problème" in text_lower:
            return "L'ERREUR FATALE À ÉVITER 🚨"
        elif "argent" in text_lower or "riche" in text_lower or "business" in text_lower:
            return "COMMENT GAGNER EN BUSINESS 💸"
        elif "pourquoi" in text_lower:
            return "POURQUOI TOUT LE MONDE SE TROMPE ⚡"
        elif "comment" in text_lower:
            return "LA MÉTHODE EXACTE EN 30 SECONDES ⏱️"
        elif "attention" in text_lower or "jamais" in text_lower:
            return "NE FAIS PLUS JAMAIS ÇA 🛑"
        else:
            return "ÉCOUTE ÇA ATTENTIVEMENT 🎯"

    def _generate_caption(self, text: str, video_title: str) -> str:
        """Génère un texte court et engageant pour la légende TikTok."""
        # Prendre un extrait percutant
        words = text.split()
        summary = " ".join(words[:18]) + "..." if len(words) > 18 else text

        lines = [
            f"👀 {summary}",
            "Tu es d'accord avec ça ? Dis-moi en commentaire 👇",
            "Enregistre la vidéo pour ne pas l'oublier 📌"
        ]
        return "\n".join(lines)

    def _select_hashtags(self, text: str) -> List[str]:
        """Sélectionne 5 à 7 hashtags pertinents."""
        base_tags = ["#pourtoi", "#fyp", "#foryou"]
        niche_tags = []

        text_lower = text.lower()
        if any(w in text_lower for w in ["argent", "business", "succès", "investir"]):
            niche_tags.extend(["#businessfrance", "#mindset", "#entrepreneuriat"])
        if any(w in text_lower for w in ["conseil", "erreur", "méthode", "règle"]):
            niche_tags.extend(["#conseil", "#apprendre", "#astuce"])
        if any(w in text_lower for w in ["musique", "son", "beat", "artiste"]):
            niche_tags.extend(["#musique", "#beatmaker", "#creation"])

        if not niche_tags:
            niche_tags = ["#conseil", "#motivation", "#culture"]

        all_tags = base_tags + niche_tags[:4]
        return all_tags

    def export_summary_sheet(self, package: Dict[str, Any], output_path: str):
        """Crée une fiche mémo prête à copier-coller pour Karl."""
        content = f"""============================================================
📱 FICHE PUBLICATION TIKTOK — SOCIÉTÉ AUTONOME (KARL)
============================================================

🎯 ACCROCHE VIDÉO (HOOK) :
{package['hook_banner']}

📝 DESCRIPTION DU POST (À COPIER-COLLER DANS TIKTOK) :
------------------------------------------------------------
{package['full_post_text']}
------------------------------------------------------------

📈 CONSEILS STRATÉGIQUES GROWTH-BOT :
- Rétention estimée : {package['estimated_retention']}
- Appel à l'action : {package['cta']}
- Astuce TikTok : Réponds aux 3 premiers commentaires dans les 30 minutes suivant la publication pour booster la viralité !

============================================================
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
