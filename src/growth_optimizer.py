import json
import re
from typing import Dict, Any, List

class GrowthOptimizer:
    """
    Sous-agent Growth-Bot / Spécialiste TikTok Viralité & Monétisation.
    Génère l'ensemble du package stratégique pour chaque extrait :
    - Hook percutant pour stopper le swipe
    - Description optimisée SEO TikTok avec CTA (Appel à l'action)
    - Sélection des hashtags viraux
    - Meilleur créneau horaire recommandé pour poster
    - Redirection vers l'écosystème Karl Studio (Waitlist / Musique)
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
        estimated_retention = min(89, int(65 + clip_info.get("score", 10) * 1.5))

        # 5. Créneaux de publication recommandés (Algorithme TikTok France)
        posting_slots = [
            "Midi : 12h00 - 13h30 (Pic de pause déjeuner)",
            "Soirée : 18h30 - 20h45 (Pic de forte audience active)",
            "Dimanche soir : 19h00 - 21h30 (Record hebdomadaire d'engagement)"
        ]

        package = {
            "hook_banner": hook_banner,
            "caption": caption,
            "hashtags": hashtags,
            "full_post_text": f"{caption}\n\n{' '.join(hashtags)}",
            "estimated_retention": f"{estimated_retention}%",
            "recommended_audio": "Son tendance ou voix originale avec boost de volume",
            "cta": "Lien en bio pour découvrir Karl Studio & rejoindre la liste VIP 🎵",
            "recommended_schedule": posting_slots,
            "karl_studio_link": "https://digrekarlito11-eng.github.io/karl-studio/"
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
        elif "musique" in text_lower or "beat" in text_lower:
            return "LES COULISSES DU STUDIO DE PRODUCTION 🎵"
        else:
            return "ÉCOUTE ÇA ATTENTIVEMENT 🎯"

    def _generate_caption(self, text: str, video_title: str) -> str:
        """Génère un texte court et engageant pour la légende TikTok."""
        words = text.split()
        summary = " ".join(words[:18]) + "..." if len(words) > 18 else text

        lines = [
            f"👀 {summary}",
            "Tu valides ou pas ? Dis-moi ton avis en commentaire 👇",
            "🔗 Lien en bio pour accéder au hub Karl Studio 🚀",
            "Enregistre la vidéo pour l'appliquer plus tard 📌"
        ]
        return "\n".join(lines)

    def _select_hashtags(self, text: str) -> List[str]:
        """Sélectionne 5 à 7 hashtags ciblés."""
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
        """Crée une fiche mémo complète pour Karl."""
        slots_str = "\n".join(f"  • {s}" for s in package['recommended_schedule'])
        content = f"""============================================================
📱 FICHE STRATÉGIQUE PUBLICATION TIKTOK — KARL STUDIO
============================================================

🎯 ACCROCHE VIDÉO (HOOK BANDEAU SUPÉRIEUR) :
{package['hook_banner']}

📝 DESCRIPTION DU POST (À COPIER-COLLER DANS TIKTOK) :
------------------------------------------------------------
{package['full_post_text']}
------------------------------------------------------------

⏰ CRÉNEAUX HORAIRES RECOMMANDÉS POUR PUBLIER :
{slots_str}

📈 CONSEILS D'OPTIMISATION GROWTH-BOT :
- Rétention estimée : {package['estimated_retention']}
- Appel à l'action : {package['cta']}
- Conversion : Oriente le trafic vers {package['karl_studio_link']}
- Règle d'or : Réponds aux 3 premiers commentaires dans les 30 premières minutes pour déclencher l'algorithme "Pour Toi" !

============================================================
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
