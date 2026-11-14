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

        # 1. Détermination du Hook pour le bandeau supérieur de la vidéo (Gospel Intelligence)
        hook_banner = clip_info.get("recommended_hook") or self._generate_hook_banner(first_sentence, text)

        # 2. Appel à l'action pour maximiser les commentaires (Comment Magnet)
        cta = clip_info.get("recommended_cta") or "Écris 'AMEN' en commentaire pour sceller cette bénédiction 👇"

        # 3. Génération de la description TikTok (Caption)
        caption = self._generate_caption(text, video_title, cta)

        # 4. Sélection des hashtags performants (Chrétien, Foi, Prédicateurs, Côte d'Ivoire, Viral)
        hashtags = self._select_hashtags(text, video_title)

        # 5. Score de rétention prévisionnel (optimisé pour vidéos de 1 à 2 min)
        base_score = clip_info.get("score", 10)
        estimated_retention = min(95, int(72 + (base_score % 22)))

        # 6. Créneaux de publication recommandés pour la Côte d'Ivoire (Fuseau horaire GMT / Abidjan)
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
            "cta": cta,
            "recommended_schedule": posting_slots,
            "location_focus": "Côte d'Ivoire (GMT / Abidjan) & Diaspora Francophone",
            "karl_studio_link": "https://digrekarlito11-eng.github.io/karl-studio/"
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

    def _generate_caption(self, text: str, video_title: str, cta: str = "Écris 'AMEN' en commentaire pour sceller cette bénédiction 👇") -> str:
        """Génère un texte engageant spécial communauté chrétienne."""
        words = text.split()
        summary = " ".join(words[:18]) + "..." if len(words) > 18 else text

        lines = [
            f"📖 {summary}",
            "Reçois cette parole dans ta vie et partage-la à quelqu'un qui a besoin d'être fortifié aujourd'hui. 🕊️",
            cta,
            "Enregistre cette vidéo pour la réécouter dans tes moments de prière 📌"
        ]
        return "\n".join(lines)

    def _select_hashtags(self, text: str, video_title: str = "") -> List[str]:
        """Sélectionne des hashtags viraux chrétiens et géolocalisés Côte d'Ivoire."""
        base_tags = ["#chretien", "#tiktokchretien", "#pourtoi", "#fyp"]
        local_tags = ["#cotedivoire", "#abidjan"]
        theme_tags = ["#priere", "#foi", "#jesus", "#predication"]

        combined = (text + " " + video_title).lower()

        # Tags spécifiques aux prédicateurs et thématiques clés
        if any(w in combined for w in ["mariage", "foyer", "femme", "mari", "conjoint", "célibat"]):
            theme_tags.append("#mariagechretien")
            theme_tags.append("#marcelotunasi")
        if any(w in combined for w in ["destinée", "destinee", "pensée", "mentalité"]):
            theme_tags.append("#yvancastanou")
            theme_tags.append("#destinee")
        if any(w in combined for w in ["blocage", "autel", "cycle", "malédiction", "sanogo"]):
            theme_tags.append("#mohamedsanogo")
            theme_tags.append("#delivrance")
        if any(w in combined for w in ["blessure", "guérison", "guerison", "coeur", "ondo"]):
            theme_tags.append("#julianaondo")
            theme_tags.append("#guerison")
        if any(w in combined for w in ["jeunesse", "esprit de nuit", "djatti"]):
            theme_tags.append("#yannickdjatti")
            theme_tags.append("#reveil")

        all_tags = base_tags + local_tags + theme_tags[:5]
        # Dé-doublonnage tout en gardant l'ordre
        seen = set()
        deduped = []
        for tag in all_tags:
            if tag not in seen:
                seen.add(tag)
                deduped.append(tag)
        return deduped

    def export_summary_sheet(self, package: Dict[str, Any], output_path: str):
        """Crée une fiche mémo complète pour Karl."""
        slots_str = "\n".join(f"  • {s}" for s in package.get('recommended_schedule', []))
        content = f"""============================================================
📱 FICHE STRATÉGIQUE PUBLICATION TIKTOK — KARL STUDIO
============================================================

🎯 ACCROCHE VIDÉO (HOOK BANDEAU SUPÉRIEUR) :
{package.get('hook_banner', '')}

📝 DESCRIPTION DU POST (À COPIER-COLLER DANS TIKTOK) :
------------------------------------------------------------
{package.get('full_post_text', '')}
------------------------------------------------------------

⏰ CRÉNEAUX HORAIRES RECOMMANDÉS POUR PUBLIER :
{slots_str}

📈 CONSEILS D'OPTIMISATION GROWTH-BOT :
- Rétention estimée : {package.get('estimated_retention', 'N/A')}
- Appel à l'action : {package.get('cta', '')}
- Ciblage géographique (location_focus) : {package.get('location_focus', "Côte d'Ivoire (GMT / Abidjan) & Diaspora")}
- Conversion : Oriente le trafic vers {package.get('karl_studio_link', 'https://digrekarlito11-eng.github.io/karl-studio/')}
- Règle d'or : Réponds aux 3 premiers commentaires dans les 30 premières minutes pour déclencher l'algorithme "Pour Toi" !

============================================================
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
