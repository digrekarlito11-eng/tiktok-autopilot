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

        # 1. Détermination du Hook pour le bandeau supérieur de la vidéo (Prédication & Foi)
        hook_banner = self._generate_hook_banner(first_sentence, text)

        # 2. Génération de la description TikTok (Caption)
        caption = self._generate_caption(text, video_title)

        # 3. Sélection des hashtags performants (Chrétien, Foi, Côte d'Ivoire, Viral)
        hashtags = self._select_hashtags(text)

        # 4. Score de rétention prévisionnel
        estimated_retention = min(92, int(70 + clip_info.get("score", 10) * 1.4))

        # 5. Créneaux de publication recommandés pour la Côte d'Ivoire (Fuseau horaire GMT / Abidjan)
        posting_slots = [
            "🌅 Matin (05h30 - 06h45 GMT) : Prière & Parole matinale (Fort taux de partage dès le réveil)",
            "☀️ Midi (12h30 - 13h45 GMT) : Pause déjeuner & Exhortation quotidienne",
            "🌙 Soir (19h30 - 21h30 GMT) : Déclaration de foi & Prière du soir avant de dormir",
            "⛪ Dimanche (14h00 - 16h00 & 19h00 - 22h00 GMT) : Pic hebdomadaire chrétien maximal"
        ]

        package = {
            "hook_banner": hook_banner,
            "caption": caption,
            "hashtags": hashtags,
            "full_post_text": f"{caption}\n\n{' '.join(hashtags)}",
            "estimated_retention": f"{estimated_retention}%",
            "recommended_audio": "Voix originale claire ou fond instrumental Gospel doux",
            "cta": "Écris 'AMEN' en commentaire si tu reçois cette parole 🙏",
            "recommended_schedule": posting_slots,
            "location_focus": "Côte d'Ivoire (GMT / Abidjan) & Diaspora Francophone"
        }

        return package

    def _generate_hook_banner(self, first_sentence: str, full_text: str) -> str:
        """Produit une phrase choc courte pour le bandeau supérieur spécial prédication chrétienne."""
        text_lower = (first_sentence + " " + full_text).lower()

        if any(w in text_lower for w in ["prophétie", "prophétique", "annoncer"]):
            return "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️"
        elif any(w in text_lower for w in ["miracle", "impossible", "témoignage"]):
            return "LE MIRACLE QUE TU ATTENDS ARRIVE ⚡"
        elif any(w in text_lower for w in ["combat", "ennemi", "délivrance", "victoire"]):
            return "TA VICTOIRE EST PROCHE DÉCLARE-LE ⚔️"
        elif any(w in text_lower for w in ["prière", "prier", "demande"]):
            return "FAIS CETTE PRIÈRE PUISSANTE 🙏"
        elif any(w in text_lower for w in ["épreuve", "douleur", "pleurer", "difficile"]):
            return "POURQUOI CETTE ÉPREUVE DANS TA VIE ? 📖"
        elif any(w in text_lower for w in ["bénédiction", "bénir", "grâce", "élévation"]):
            return "CETTE PAROLE VA CHANGER TA VIE ✨"
        elif any(w in text_lower for w in ["foi", "croire", "douter"]):
            return "NE DOUTE PLUS DE TA DESTINÉE 👑"
        else:
            return "DIEU A UN MESSAGE POUR TOI AUJOURD'HUI ✝️"

    def _generate_caption(self, text: str, video_title: str) -> str:
        """Génère un texte engageant spécial communauté chrétienne."""
        words = text.split()
        summary = " ".join(words[:18]) + "..." if len(words) > 18 else text

        lines = [
            f"📖 {summary}",
            "Reçois cette parole dans ta vie et partage-la à quelqu'un qui a besoin d'être fortifié aujourd'hui. 🕊️",
            "Écris 'AMEN' en commentaire pour sceller cette bénédiction 👇",
            "Enregistre cette vidéo pour la réécouter dans tes moments de prière 📌"
        ]
        return "\n".join(lines)

    def _select_hashtags(self, text: str) -> List[str]:
        """Sélectionne des hashtags viraux chrétiens et géolocalisés Côte d'Ivoire."""
        base_tags = ["#chretien", "#tiktokchretien", "#pourtoi", "#fyp"]
        local_tags = ["#cotedivoire", "#abidjan", "#chretienconnecte"]
        theme_tags = ["#priere", "#foi", "#jesus", "#predication", "#evangile"]

        text_lower = text.lower()
        if "prophétie" in text_lower:
            theme_tags.insert(0, "#prophetie")
        if "miracle" in text_lower:
            theme_tags.insert(0, "#miracle")
        if "combat" in text_lower:
            theme_tags.insert(0, "#combatspirituel")

        all_tags = base_tags + local_tags[:2] + theme_tags[:4]
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
