import json
import os
import re
from typing import Dict, Any, List, Optional


class GrowthOptimizer:
    """
    Sous-agent Growth-Bot / Spécialiste TikTok Viralité & Monétisation.
    Génère l'ensemble du package stratégique pour chaque extrait :
    - Hook percutant pour stopper le swipe
    - Description optimisée SEO TikTok avec CTA (Appel à l'action)
    - Sélection des hashtags viraux chrétiens (3 packs ciblés de 5 hashtags)
    - Meilleur créneau horaire recommandé pour poster
    - Redirection vers l'écosystème Karl Studio (Waitlist / Musique)
    """

    HASHTAG_PACKS: Dict[str, List[str]] = {
        "predication": [
            "#Predication",
            "#Evangile",
            "#JesusChrist",
            "#FoiEnDieu",
            "#ChristianTikTok",
        ],
        "priere": [
            "#Priere",
            "#PriereDuJour",
            "#JesusChrist",
            "#FoiEnDieu",
            "#CotedIvoire",
        ],
        "gospel": [
            "#Gospel",
            "#MusiqueChretienne",
            "#Louange",
            "#JesusChrist",
            "#GospelAfricain",
        ],
    }

    HASHTAG_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        "gospel": [
            "gospel", "louange", "adoration", "cantique", "chant", "chanter",
            "musique", "chanson", "chorale", "worship", "mélodie", "melodie",
            "instrument", "psaume chanté",
        ],
        "priere": [
            "prière", "priere", "prières", "prieres", "prier", "prie",
            "intercession", "jeûne", "jeune", "supplication", "délivrance",
            "delivrance", "combat spirituel", "guérison", "guerison",
            "prophétie", "prophetie", "miracle",
        ],
        "predication": [
            "prédication", "predication", "évangile", "evangile", "enseignement",
            "message", "sermon", "parole", "bible", "verset", "mariage",
            "destinée", "destinee", "foi", "pasteur", "église", "eglise",
        ],
    }

    RECOMMENDATIONS_PATH = "history/growth_recommendations.json"

    def __init__(self, recommendations_path: Optional[str] = None):
        self.recommendations_path = recommendations_path or self.RECOMMENDATIONS_PATH

    DEFAULT_HOOK = "DIEU A UN MESSAGE POUR TOI AUJOURD'HUI ✝️"
    GOSPEL_DEFAULT_FALLBACK_HOOK = "TU N'ES PAS NÉ POUR ACCOMPAGNER LES AUTRES 🕊️"

    @staticmethod
    def _has_any_word(text_lower: str, words: List[str]) -> bool:
        """Vérifie la présence d'au moins un mot ou expression entière (frontières de mots \b)."""
        for w in words:
            if w in ("foi", "mari", "paix"):
                pattern = rf"\b{re.escape(w)}\b"
            else:
                pattern = rf"\b{re.escape(w)}s?\b"
            if re.search(pattern, text_lower):
                return True
        return False

    def generate_growth_package(self, clip_info: Dict[str, Any], video_title: str) -> Dict[str, Any]:
        text = clip_info.get("text", "")
        first_sentence = clip_info.get("first_sentence", "")

        # 1. Détermination du Hook pour le bandeau supérieur de la vidéo
        # Priorité au Hook de la première phrase ou à l'archétype GospelIntelligence quand pertinent
        first_hook = self._generate_hook_banner(first_sentence, "")
        gospel_hook = clip_info.get("recommended_hook")
        gospel_meta = clip_info.get("gospel_meta") if isinstance(clip_info.get("gospel_meta"), dict) else {}
        gospel_matched = gospel_meta.get("matched_keywords") or clip_info.get("matched_keywords") or []

        if first_hook != self.DEFAULT_HOOK:
            hook_banner = first_hook
        elif gospel_hook and (gospel_hook != self.GOSPEL_DEFAULT_FALLBACK_HOOK or gospel_matched):
            hook_banner = gospel_hook
        else:
            hook_banner = self._generate_hook_banner(first_sentence, text)
            if hook_banner == self.DEFAULT_HOOK and gospel_hook:
                hook_banner = gospel_hook

        # 2. Appel à l'action pour maximiser les commentaires (Comment Magnet)
        recommendations = self._load_dynamic_recommendations()
        default_cta = recommendations.get("recommended_cta") or "Écris 'AMEN' en commentaire pour sceller cette bénédiction 👇"
        cta = clip_info.get("recommended_cta") or default_cta

        # 3. Génération de la description TikTok (Caption)
        caption = self._generate_caption(text, video_title, cta)

        # 4. Sélection du pack de 5 hashtags chrétiens ciblés (Prédication / Prière / Gospel)
        hashtag_pack = self._select_hashtag_category(text, video_title)
        hashtags = self._select_hashtags(text, video_title)

        # 5. Score de rétention prévisionnel (optimisé pour vidéos TikTok)
        base_score = clip_info.get("score", 10)
        estimated_retention = min(92, int(70 + base_score * 1.4))

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
            "hashtag_pack": hashtag_pack,
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

    def _load_dynamic_recommendations(self) -> Dict[str, Any]:
        """Charge les recommandations générées par l'agent d'analyse 24/7 si disponibles."""
        if not self.recommendations_path or not os.path.exists(self.recommendations_path):
            return {}
        try:
            with open(self.recommendations_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _generate_hook_banner(self, first_sentence: str, full_text: str) -> str:
        """Produit une phrase choc courte pour le bandeau supérieur spécial prédication chrétienne."""
        text_lower = (first_sentence + " " + full_text).lower()

        if self._has_any_word(text_lower, ["prophétie", "prophetie", "prophétique", "prophetique", "annoncer"]):
            return "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️"
        elif self._has_any_word(text_lower, ["miracle", "impossible", "témoignage", "temoignage"]):
            return "LE MIRACLE QUE TU ATTENDS ARRIVE ⚡"
        elif self._has_any_word(text_lower, ["combat", "ennemi", "délivrance", "delivrance", "victoire"]):
            return "TA VICTOIRE EST PROCHE DÉCLARE-LE ⚔️"
        elif self._has_any_word(text_lower, ["mariage", "foyer", "femme", "mari", "conjoint", "célibat", "celibat"]):
            return "LA VÉRITÉ SUR LE MARIAGE QUE PERSONNE N'OSE DIRE ⚡"
        elif self._has_any_word(text_lower, ["blessure", "blessures", "coeur", "cœur", "guérison", "guerison"]):
            return "DIEU A VU TES LARMES CACHÉES : REÇOIS SA GUÉRISON 🕊️"
        elif self._has_any_word(text_lower, ["blocage", "malédiction", "malediction", "autel"]):
            return "CE CYCLE DE SOUFFRANCE DANS TA FAMILLE S'ARRÊTE AUJOURD'HUI 🔥"
        elif self._has_any_word(text_lower, ["destinée", "destinee", "mindset", "pensée", "pensee", "mentalité", "mentalite"]):
            return "TU N'ES PAS NÉ POUR ACCOMPAGNER LES AUTRES 🕊️"
        elif self._has_any_word(text_lower, ["prière", "priere", "prier", "demande"]):
            return "FAIS CETTE PRIÈRE PUISSANTE 🙏"
        elif self._has_any_word(text_lower, ["épreuve", "epreuve", "douleur", "pleurer", "difficile"]):
            return "POURQUOI CETTE ÉPREUVE DANS TA VIE ? 📖"
        elif self._has_any_word(text_lower, ["bénédiction", "benediction", "bénir", "benir", "grâce", "grace", "élévation", "elevation"]):
            return "CETTE PAROLE VA CHANGER TA VIE ✨"
        elif self._has_any_word(text_lower, ["foi", "croire", "douter"]):
            return "NE DOUTE PLUS DE TA DESTINÉE 👑"
        else:
            return self.DEFAULT_HOOK

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

    def _select_hashtag_category(self, text: str, video_title: str = "") -> str:
        """Détermine le pack de hashtags le plus adapté : predication, priere ou gospel."""
        combined = f"{text or ''} {video_title or ''}".lower()
        scores: Dict[str, int] = {}
        for category, keywords in self.HASHTAG_CATEGORY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}", combined):
                    score += 1
            scores[category] = score

        if scores["gospel"] > 0 and scores["gospel"] >= scores["priere"] and scores["gospel"] >= scores["predication"]:
            return "gospel"
        if scores["priere"] > 0 and scores["priere"] >= scores["predication"]:
            return "priere"
        return "predication"

    def _select_hashtags(self, text: str, video_title: str = "") -> List[str]:
        """Sélectionne l'un des 3 packs de 5 hashtags chrétiens TikTok définis par Karl."""
        category = self._select_hashtag_category(text, video_title)
        return list(self.HASHTAG_PACKS[category])

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
