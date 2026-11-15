import re
from typing import List, Dict, Any, Optional

try:
    from .gospel_intelligence import GospelIntelligence
except ImportError:
    from gospel_intelligence import GospelIntelligence

# Mots-clés déclencheurs d'émotion, de curiosité et d'impact spirituel sur TikTok
VIRAL_KEYWORDS: Dict[str, float] = {
    # Mots-clés Spécialisés Prédications (Tunasi, Castanou, Sanogo, Ondo, Djatti)
    "mariage": 4.5,
    "foyer": 4.5,
    "conjoint": 4.0,
    "célibat": 4.0,
    "celibat": 4.0,
    "divorce": 4.0,
    "infidélité": 4.5,
    "infidelite": 4.5,
    "impudicité": 4.5,
    "impudicite": 4.5,
    "malédiction": 5.0,
    "malediction": 5.0,
    "malédictions": 5.0,
    "maledictions": 5.0,
    "blocage": 4.5,
    "blocages": 4.5,
    "autel": 4.5,
    "autels": 4.5,
    "blessure": 4.5,
    "blessures": 4.5,
    "guérison": 4.5,
    "guerison": 4.5,
    "rejet": 4.0,
    "abandon": 4.0,
    "pardon": 4.0,
    "pauvreté": 4.0,
    "pauvrete": 4.0,
    "dieu": 3.5,
    "jésus": 3.5,
    "jesus": 3.5,
    "seigneur": 3.0,
    "seigneurs": 3.0,
    "foi": 3.5,
    "prière": 3.5,
    "priere": 3.5,
    "prières": 3.5,
    "prieres": 3.5,
    "prophétie": 4.0,
    "prophetie": 4.0,
    "prophéties": 4.0,
    "propheties": 4.0,
    "bénédiction": 3.5,
    "benediction": 3.5,
    "bénédictions": 3.5,
    "benedictions": 3.5,
    "miracle": 4.0,
    "miracles": 4.0,
    "combat": 3.0,
    "combats": 3.0,
    "victoire": 3.5,
    "victoires": 3.5,
    "grâce": 3.0,
    "grace": 3.0,
    "grâces": 3.0,
    "graces": 3.0,
    "onction": 3.5,
    "onctions": 3.5,
    "éternel": 3.5,
    "eternel": 3.5,
    "éternels": 3.5,
    "eternels": 3.5,
    "destinée": 3.5,
    "destinee": 3.5,
    "destinées": 3.5,
    "destinees": 3.5,
    "témoignage": 3.5,
    "temoignage": 3.5,
    "témoignages": 3.5,
    "temoignages": 3.5,
    "délivrance": 4.0,
    "delivrance": 4.0,
    "délivrances": 4.0,
    "delivrances": 4.0,
    "promesse": 3.0,
    "promesses": 3.0,
    "épreuve": 3.0,
    "epreuve": 3.0,
    "épreuves": 3.0,
    "epreuves": 3.0,
    "élévation": 3.5,
    "elevation": 3.5,
    "parole": 2.5,
    "paroles": 2.5,
    "gloire": 2.5,
    "gloires": 2.5,
    "saint": 3.0,
    "saints": 3.0,
    "esprit": 3.5,
    "esprits": 3.5,
    "christ": 3.5,
    "christs": 3.5,
    "père": 3.0,
    "pere": 3.0,
    # Mots-clés de curiosité et d'accroche universels
    "secret": 3.0,
    "secrets": 3.0,
    "erreur": 3.0,
    "erreurs": 3.0,
    "pourquoi": 2.5,
    "comment": 2.5,
    "vérité": 2.5,
    "verite": 2.5,
    "attention": 2.5,
    "jamais": 2.0,
    "toujours": 1.5,
    "voici": 2.0,
    "écoutez": 3.0,
    "ecoutez": 3.0,
    "regarde": 2.5,
    "regardez": 2.5
}

def normalize_french_word(word: str) -> str:
    """
    Normalise un mot français pour l'extraction de moments forts :
    1. Minuscule et suppression de la ponctuation résiduelle et de dialogue (-_«»\"'()[]{}).
    2. Suppression des élisions courantes : l', d', c', qu', s', m', t', n', j'.
    3. Préservation des caractères alphabétiques (incluant les accents français).
    """
    w = word.strip("-_–—«»\"'()[]{}...,;!? ")
    w = w.lower()
    elision_pattern = r"^(?:qu|[ldcsmtnj])['’]"
    w = re.sub(elision_pattern, "", w)
    return "".join(c for c in w if c.isalpha())

def stem_french_word(word: str) -> str:
    """
    Supprime la marque du pluriel régulier français ('s' ou 'x')
    si la racine fait au moins 4 caractères alphabétiques.
    Ex: 'miracles' -> 'miracle', 'prieres' -> 'priere'.
    """
    if len(word) >= 4 and word.endswith(('s', 'x')):
        return word[:-1]
    return word

def _match_single_token(token: str) -> tuple[float, Optional[str]]:
    """Helper interne pour tester la correspondance d'un token alphabétique."""
    clean_raw = "".join(c for c in token.lower() if c.isalpha())
    if clean_raw in VIRAL_KEYWORDS:
        return VIRAL_KEYWORDS[clean_raw], clean_raw

    norm = normalize_french_word(token)
    if norm in VIRAL_KEYWORDS:
        return VIRAL_KEYWORDS[norm], norm

    stemmed = stem_french_word(norm)
    if stemmed in VIRAL_KEYWORDS:
        return VIRAL_KEYWORDS[stemmed], stemmed

    if clean_raw:
        stemmed_raw = stem_french_word(clean_raw)
        if stemmed_raw in VIRAL_KEYWORDS:
            return VIRAL_KEYWORDS[stemmed_raw], stemmed_raw

    return 0.0, None

def find_keyword_match(raw_word: str) -> tuple[float, Optional[str]]:
    """
    Vérifie si le mot brut correspond à un mot-clé viral en testant :
    1. Le mot nettoyé direct
    2. Le mot débarrassé des élisions (l', d', c', qu') et ponctuation de dialogue
    3. La forme singulière débarrassée du 's' ou 'x' terminal
    4. Les sous-mots composés par des traits d'union (ex: Jésus-Christ, Dieu-le-Père, Saint-Esprit)
    Retourne (score, mot_clé_correspondant) ou (0.0, None).
    """
    cleaned = raw_word.strip("-_–—«»\"'()[]{}...,;!? ")
    if not cleaned:
        return 0.0, None

    # 1. Tester le token complet
    score, kw = _match_single_token(cleaned)
    if score > 0:
        return score, kw

    # 2. Si mot composé par des traits d'union (ex: Jésus-Christ, Dieu-le-Père, Saint-Esprit)
    if "-" in cleaned:
        best_score = 0.0
        best_kw = None
        for part in cleaned.split("-"):
            part_cleaned = part.strip("-_–—«»\"'()[]{}...,;!? ")
            if part_cleaned:
                s, k = _match_single_token(part_cleaned)
                if s > best_score:
                    best_score = s
                    best_kw = k
        if best_score > 0:
            return best_score, best_kw

    return 0.0, None

class ClipExtractor:
    """
    Sous-agent Media-Bot & Growth-Bot / Détecteur de moments viraux.
    Analyse les phrases, repère les pics d'attention et découpe des clips
    d'une durée idéale pour TikTok (entre 1 et 2 minutes : 60s à 120s),
    calibrés pour la monétisation (>60s) et les vérités bibliques percutantes.
    Intègre l'Intelligence Spirituelle (Gospel Intelligence) sans coût d'API.
    """

    def __init__(self, min_duration: float = 60.0, max_duration: float = 120.0):
        self.min_duration = min_duration
        self.max_duration = max_duration

    def find_best_clips(self, segments: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Trouve les meilleurs extraits en combinant durée de 1 à 2 min, score viral
        et potentiel à générer des commentaires (Comment Magnet Score).
        """
        if not segments:
            return []

        candidates = []
        n = len(segments)

        # Pré-calcul O(n) du score viral, des mots-clés et du nombre de mots par segment
        seg_scores: List[float] = []
        seg_keywords: List[set] = []
        seg_word_counts: List[int] = []

        for seg in segments:
            seg_text = seg.get("text", "")
            words = seg_text.split()
            seg_word_counts.append(len(words))
            s_score = 0.0
            s_kws = set()
            for w in words:
                kw_score, kw_matched = find_keyword_match(w)
                if kw_score > 0 and kw_matched:
                    s_score += kw_score
                    s_kws.add(kw_matched)
            seg_scores.append(s_score)
            seg_keywords.append(s_kws)

        for i in range(n):
            start_t = segments[i]["start"]
            current_text = []
            viral_score = 0.0
            word_count = 0
            matched_keywords_set = set()

            for j in range(i, n):
                end_t = segments[j]["end"]
                seg_text = segments[j]["text"]
                current_text.append(seg_text)
                viral_score += seg_scores[j]
                word_count += seg_word_counts[j]
                matched_keywords_set.update(seg_keywords[j])

                duration = end_t - start_t
                if duration >= self.min_duration:
                    if duration <= self.max_duration:
                        # Analyse d'impact spirituel via Gospel Intelligence (Growth-Bot)
                        cand_text = " ".join(current_text)
                        gospel_meta = GospelIntelligence.analyze_segment_spirituality(cand_text)

                        # Bonus de densité de mots et cadence
                        cadence = word_count / duration  # mots par seconde
                        cadence_bonus = 1.0 if 1.8 <= cadence <= 4.2 else 0.6

                        # Score global : Mots clés + Aimant à commentaires (Comment Magnet)
                        total_score = (viral_score + gospel_meta["comment_magnet_score"] + 1.0) * cadence_bonus * (word_count / 15.0)

                        candidates.append({
                            "start": round(start_t, 2),
                            "end": round(end_t, 2),
                            "duration": round(duration, 2),
                            "score": round(total_score, 2),
                            "text": cand_text,
                            "first_sentence": current_text[0],
                            "segments": segments[i:j+1],
                            "matched_keywords": sorted(list(matched_keywords_set)),
                            "gospel_meta": gospel_meta,
                            "dominant_archetype": gospel_meta["dominant_archetype"],
                            "recommended_hook": gospel_meta["recommended_hook"],
                            "recommended_cta": gospel_meta["recommended_cta"]
                        })
                    else:
                        break

        if not candidates:
            # Fallback si aucun segment ne fait 60s
            total_duration = segments[-1]["end"] - segments[0]["start"]
            end_time = min(segments[0]["start"] + self.max_duration, segments[-1]["end"])
            fb_text = " ".join(s["text"] for s in segments)
            fb_gospel = GospelIntelligence.analyze_segment_spirituality(fb_text)

            return [{
                "start": segments[0]["start"],
                "end": end_time,
                "duration": round(end_time - segments[0]["start"], 2),
                "score": 10.0,
                "text": fb_text,
                "first_sentence": segments[0]["text"],
                "segments": segments,
                "matched_keywords": [],
                "gospel_meta": fb_gospel,
                "dominant_archetype": fb_gospel["dominant_archetype"],
                "recommended_hook": fb_gospel["recommended_hook"],
                "recommended_cta": fb_gospel["recommended_cta"]
            }]

        # Trier par score décroissant et dédoublonner pour sélectionner jusqu'à top_k extraits distincts
        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = []
        for cand in candidates:
            overlap = False
            for s in selected:
                # Éviter le chevauchement excessif (tolère jusqu'à 5s de marge aux extrémités)
                if not (cand["end"] <= s["start"] + 5.0 or cand["start"] >= s["end"] - 5.0):
                    overlap = True
                    break
            if not overlap:
                selected.append(cand)
                if len(selected) >= top_k:
                    break

        if not selected:
            selected = candidates[:top_k]

        return selected

    # Alias pour conformité aux spécifications d'interface
    extract_highlights = find_best_clips
