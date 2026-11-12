from typing import List, Dict, Any

# Mots-clés déclencheurs d'émotion et de curiosité sur TikTok
VIRAL_KEYWORDS = {
    "secret": 3.0,
    "erreur": 3.0,
    "pourquoi": 2.5,
    "comment": 2.5,
    "argent": 2.5,
    "vérité": 2.5,
    "problème": 2.0,
    "règle": 2.0,
    "méthode": 2.0,
    "jamais": 2.0,
    "toujours": 1.5,
    "résultat": 2.0,
    "attention": 2.5,
    "clé": 2.0,
    "business": 2.0,
    "succès": 2.0,
    "arnaque": 2.5,
    "personne": 2.0,
    "voici": 2.0,
    "voilà": 1.5
}

class ClipExtractor:
    """
    Sous-agent Media-Bot & Growth-Bot / Détecteur de moments viraux.
    Analyse les phrases, repère les pics d'attention et découpe des clips
    d'une durée idéale pour TikTok (entre 30 et 60 secondes).
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

            for j in range(i, n):
                end_t = segments[j]["end"]
                seg_text = segments[j]["text"]
                current_text.append(seg_text)

                # Calcul du score viral basé sur les mots clés
                words = seg_text.lower().split()
                for w in words:
                    clean_w = "".join(c for c in w if c.isalpha())
                    if clean_w in VIRAL_KEYWORDS:
                        viral_score += VIRAL_KEYWORDS[clean_w]

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
                            "segments": segments[i:j+1]
                        })
                    else:
                        break

        if not candidates:
            # Fallback simple si la vidéo est courte
            total_duration = segments[-1]["end"] - segments[0]["start"]
            end_time = min(segments[0]["start"] + self.max_duration, segments[-1]["end"])
            return [{
                "start": segments[0]["start"],
                "end": end_time,
                "duration": round(end_time - segments[0]["start"], 2),
                "score": 10.0,
                "text": " ".join(s["text"] for s in segments),
                "first_sentence": segments[0]["text"],
                "segments": segments
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
