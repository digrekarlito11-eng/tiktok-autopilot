import re
from typing import List, Dict, Any, Optional

# Mots-clés déclencheurs d'émotion, de curiosité et d'impact spirituel sur TikTok
VIRAL_KEYWORDS: Dict[str, float] = {
    # Mots-clés Foi & Prédication Chrétienne (Haute intensité émotionnelle)
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
    d'une durée idéale pour TikTok (entre 30 et 60 secondes).
    Intègre la lemmatisation / normalisation NLP pour le français (élisions, pluriels).
    """

    def __init__(self, min_duration: float = 25.0, max_duration: float = 58.0):
        self.min_duration = min_duration
        self.max_duration = max_duration

    def find_best_clips(self, segments: List[Dict[str, Any]], top_k: int = 1) -> List[Dict[str, Any]]:
        """
        Trouve les meilleurs extraits en combinant durée idéale et score viral.
        """
        if not segments:
            return []

        candidates = []
        n = len(segments)

        for i in range(n):
            start_t = segments[i]["start"]
            current_text = []
            viral_score = 0.0
            matched_keywords_set = set()

            for j in range(i, n):
                end_t = segments[j]["end"]
                seg_text = segments[j]["text"]
                current_text.append(seg_text)

                # Calcul du score viral basé sur les mots clés français avec élision & pluriels
                words = seg_text.split()
                for w in words:
                    kw_score, kw_matched = find_keyword_match(w)
                    if kw_score > 0 and kw_matched:
                        viral_score += kw_score
                        matched_keywords_set.add(kw_matched)
                    cleaned_w = w.strip("-_–—«»\"'()[]{}...,;!? ")
                    if "-" in cleaned_w:
                        for part in cleaned_w.split("-"):
                            p_score, p_kw = find_keyword_match(part)
                            if p_score > 0 and p_kw and p_kw != kw_matched:
                                viral_score += p_score
                                matched_keywords_set.add(p_kw)

                duration = end_t - start_t
                if duration >= self.min_duration:
                    if duration <= self.max_duration:
                        # Score normalisé par la fluidité
                        # Bonus de densité de mots
                        word_count = sum(len(t.split()) for t in current_text)
                        cadence = word_count / duration # mots par seconde

                        # Une bonne cadence parlée se situe entre 2.2 et 3.5 mots/sec
                        cadence_bonus = 1.0 if 2.0 <= cadence <= 4.0 else 0.5
                        final_score = (viral_score + 1.0) * cadence_bonus * (word_count / 10.0)

                        candidates.append({
                            "start": round(start_t, 2),
                            "end": round(end_t, 2),
                            "duration": round(duration, 2),
                            "score": round(final_score, 2),
                            "text": " ".join(current_text),
                            "first_sentence": current_text[0],
                            "segments": segments[i:j+1],
                            "matched_keywords": sorted(list(matched_keywords_set))
                        })
                    else:
                        break

        if not candidates:
            # Fallback simple si la vidéo est courte
            total_duration = segments[-1]["end"] - segments[0]["start"]
            end_time = min(segments[0]["start"] + self.max_duration, segments[-1]["end"])
            fallback_matched = set()
            for s in segments:
                for w in s["text"].split():
                    kw_score, kw_matched = find_keyword_match(w)
                    if kw_score > 0 and kw_matched:
                        fallback_matched.add(kw_matched)

            return [{
                "start": segments[0]["start"],
                "end": end_time,
                "duration": round(end_time - segments[0]["start"], 2),
                "score": 10.0,
                "text": " ".join(s["text"] for s in segments),
                "first_sentence": segments[0]["text"],
                "segments": segments,
                "matched_keywords": sorted(list(fallback_matched))
            }]

        # Trier par score décroissant et dédoublonner les plages trop proches
        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = []
        for cand in candidates:
            # Vérifier qu'il ne chevauche pas un clip déjà sélectionné à plus de 50%
            overlap = False
            for s in selected:
                if not (cand["end"] < s["start"] or cand["start"] > s["end"]):
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
