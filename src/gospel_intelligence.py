"""
Sous-agent Growth-Bot : Module d'Intelligence Comportementale TikTok Chrétien (Gospel Intelligence).
Fonctionne à 100% en local sans coût d'API (0 crédit consommé).

Analyse les transcripts de prédications et repère les 5 archétypes viraux
qui déclenchent des millions de vues et des milliers de commentaires sur TikTok :
1. Vérités Tranchantes & Réalité Crue du Couple (Style Marcelo Tunasi)
2. Destinée, Mindset Biblique & Réussite Pratique (Style Yvan & Yves Castanou)
3. Clameur Prophétique & Brisement des Liens Familiaux (Style Mohamed Sanogo)
4. Guérison Intérieure, Vulnérabilité & Cœur Brisé (Style Juliana Ondo)
5. Jeunesse Radicale, Sanctification & Autorité Spirituelle (Style Yannick Djatti)
"""

import re
from typing import Dict, Any, List, Tuple

# Dictionnaire thématique pondéré des vérités bibliques et de vie à fort impact
GOSPEL_ARCHETYPES = {
    "MARIAGE_ET_VERITE_CRUE": {
        "preachers": ["Marcelo Tunasi"],
        "weight": 4.5,
        "keywords": [
            "mariage", "foyer", "femme", "mari", "conjoint", "célibat", "celibat",
            "divorce", "infidélité", "infidelite", "sexe", "impudicité", "impudicite",
            "hypocrisie", "respect", "soumission", "amour", "relation", "séduction",
            "vérité", "charnel", "chair", "mensonge", "tromper", "tromperie"
        ],
        "default_hook": "LA VÉRITÉ SUR LE MARIAGE QUE PERSONNE N'OSE DIRE ⚡",
        "cta": "Partage cette vérité à quelqu'un qui veut réussir son foyer 🙏"
    },
    "DESTINEE_ET_MINDSET": {
        "preachers": ["Yvan Castanou", "Yves Castanou"],
        "weight": 4.2,
        "keywords": [
            "destinée", "destinee", "potentiel", "pensée", "pensees", "langue",
            "vision", "succès", "succes", "pauvreté", "mentalité", "mentalite",
            "grandeur", "transformation", "responsabilité", "responsabilite",
            "obéissance", "obeissance", "identité", "identite", "roi", "règne"
        ],
        "default_hook": "TU N'ES PAS NÉ POUR ACCOMPAGNER LES AUTRES 🕊️",
        "cta": "Enregistre cette vidéo pour renouveler tes pensées chaque matin 📌"
    },
    "BRISEMENT_ET_PROPHETIE": {
        "preachers": ["Mohamed Sanogo"],
        "weight": 5.0,
        "keywords": [
            "blocage", "blocages", "malédiction", "malediction", "famille", "cycle",
            "retard", "limitation", "pauvre", "misère", "misere", "chômage", "chomage",
            "ennemi", "délivrance", "delivrance", "brisement", "autel", "autels",
            "je décrète", "je decrete", "je déclare", "je declare", "saison", "témoignage"
        ],
        "default_hook": "CE CYCLE DE SOUFFRANCE DANS TA FAMILLE S'ARRÊTE AUJOURD'HUI 🔥",
        "cta": "Écris 'AMEN' avec foi pour sceller cette délivrance dans ta famille 👇"
    },
    "GUERISON_INTERIEURE": {
        "preachers": ["Juliana Ondo"],
        "weight": 4.6,
        "keywords": [
            "blessure", "blessures", "cœur", "coeur", "rejet", "abandon", "trahison",
            "larmes", "pleurer", "douleur", "pardon", "pardonner", "culpabilité",
            "culpabilite", "honte", "restauration", "consolation", "baume", "amour de dieu",
            "âme", "ame", "guérison", "guerison", "trauma"
        ],
        "default_hook": "DIEU A VU TES LARMES CACHÉES : REÇOIS SA GUÉRISON 🕊️",
        "cta": "Écris 'SEIGNEUR GUÉRIS MON CŒUR' en commentaire si tu as besoin de paix 🙏"
    },
    "COMBAT_ET_REVEIL": {
        "preachers": ["Yannick Djatti"],
        "weight": 4.3,
        "keywords": [
            "réveil", "reveil", "jeunesse", "esprit de nuit", "mari de nuit",
            "femme de nuit", "feu", "saint-esprit", "onction", "autorité",
            "autorite", "puissance", "chaînes", "chaines", "combat spirituel",
            "prière efficace", "jeûne", "jeune", "consécration", "consecration"
        ],
        "default_hook": "LE COMBAT SPIRITUEL QUE BEAUCOUP IGNORENT ⚔️",
        "cta": "Écris 'VICTOIRE AU NOM DE JÉSUS' et partage ce message ⚡"
    }
}

class GospelIntelligence:
    """
    Moteur analytique sans frais pour détecter les pépites virales spirituelles.
    """

    @staticmethod
    def analyze_segment_spirituality(text: str) -> Dict[str, Any]:
        """
        Analyse un extrait de texte pour classifier le type d'impact biblique
        et calculer le potentiel d'engagement (vues + commentaires).
        """
        clean_text = text.lower()
        archetype_scores: Dict[str, float] = {}
        detected_keywords: Dict[str, List[str]] = {}

        for arch_key, arch_data in GOSPEL_ARCHETYPES.items():
            score = 0.0
            found_words = []
            for kw in arch_data["keywords"]:
                # Recherche par mot entier ou sous-chaîne significative
                matches = re.findall(rf"\b{re.escape(kw)}", clean_text)
                if matches:
                    score += len(matches) * arch_data["weight"]
                    found_words.append(kw)
            archetype_scores[arch_key] = score
            detected_keywords[arch_key] = found_words

        # Trouver l'archétype dominant
        best_archetype = max(archetype_scores, key=archetype_scores.get)
        best_score = archetype_scores[best_archetype]

        # Si aucun mot spécifique n'est trouvé, fallback sur vérité générale
        if best_score == 0:
            best_archetype = "DESTINEE_ET_MINDSET"
            best_score = 5.0

        archetype_info = GOSPEL_ARCHETYPES[best_archetype]

        # Calcul du 'Comment Magnet Score' (Potentiel à générer des commentaires)
        # Les thèmes de brisement familial (Sanogo) et de couple (Tunasi) génèrent le plus de réactions
        comment_multiplier = 1.3 if best_archetype in ["BRISEMENT_ET_PROPHETIE", "MARIAGE_ET_VERITE_CRUE"] else 1.1
        final_comment_magnet_score = round(best_score * comment_multiplier, 2)

        return {
            "dominant_archetype": best_archetype,
            "preacher_influence": archetype_info["preachers"],
            "comment_magnet_score": final_comment_magnet_score,
            "recommended_hook": archetype_info["default_hook"],
            "recommended_cta": archetype_info["cta"],
            "matched_keywords": detected_keywords.get(best_archetype, [])
        }

    @staticmethod
    def generate_viral_comment_prompt(archetype: str) -> str:
        """
        Retourne une phrase d'appel à l'action calibrée pour l'algorithme TikTok.
        """
        arch_data = GOSPEL_ARCHETYPES.get(archetype, GOSPEL_ARCHETYPES["DESTINEE_ET_MINDSET"])
        return arch_data["cta"]
