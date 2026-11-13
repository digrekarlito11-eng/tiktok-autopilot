import os
import re
import subprocess
from typing import List, Dict, Any, Optional

def parse_vtt_timestamp(ts_str: str) -> float:
    """Convertit un timestamp VTT '00:01:23.456' ou '01:23.456' en secondes."""
    parts = ts_str.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])

def clean_subtitle_text(text: str) -> str:
    """Nettoie le texte des balises HTML et répétitions."""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = " ".join(clean.split())
    return clean

def deduplicate_rolling_text(prev_text: str, curr_text: str) -> str:
    """
    Supprime la répétition due aux sous-titres à fenêtre roulante (rolling-window captions)
    générés automatiquement par YouTube/TikTok.
    Compare la fin de prev_text et le début de curr_text et élimine le chevauchement.
    """
    if not prev_text or not curr_text:
        return curr_text

    prev_words = prev_text.split()
    curr_words = curr_text.split()

    # Mots normalisés (insensibles à la casse et ponctuation) pour la détection
    norm_prev = [re.sub(r'[^\w]', '', w.lower()) for w in prev_words]
    norm_curr = [re.sub(r'[^\w]', '', w.lower()) for w in curr_words]

    # Chercher le plus grand préfixe de curr_words qui correspond à un suffixe de prev_words
    max_k = min(len(prev_words), len(curr_words))
    for k in range(max_k, 0, -1):
        if norm_prev[-k:] == norm_curr[:k]:
            # Dédupliquer si le chevauchement est d'au moins 2 mots,
            # ou si l'un des segments est constitué d'un seul mot complet répété
            if k >= 2 or len(prev_words) == 1 or len(curr_words) == 1:
                trimmed = curr_words[k:]
                return " ".join(trimmed)

    return curr_text

class VideoTranscriber:
    """
    Sous-agent Media-Bot / Transcripteur intelligent.
    1. Analyse d'abord le fichier de sous-titres extrait (rapide, 0 coût).
    2. Si aucun sous-titre n'existe, utilise faster-whisper en local.
    """

    def __init__(self, model_size: str = "tiny"):
        self.model_size = model_size
        self._whisper_model = None

    def transcribe(self, video_path: str, subtitle_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extrait les segments textuels horodatés.
        """
        if subtitle_path and os.path.exists(subtitle_path):
            print(f"⚡ [Media-Bot] Analyse instantanée des sous-titres natifs...")
            segments = self._parse_vtt(subtitle_path)
            if segments and len(segments) > 0:
                print(f"✅ [Media-Bot] {len(segments)} segments textuels extraits avec succès.")
                return segments

        print(f"🎙️ [Media-Bot] Transcription via IA locale (faster-whisper '{self.model_size}')...")
        return self._transcribe_with_whisper(video_path)

    def _parse_vtt(self, vtt_path: str) -> List[Dict[str, Any]]:
        segments = []
        with open(vtt_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        current_start = None
        current_end = None
        current_text = []
        last_cue_text: Optional[str] = None

        time_pattern = re.compile(r'(\d+:\d+:[\d\.]+|\d+:[\d\.]+)\s*-->\s*(\d+:\d+:[\d\.]+|\d+:[\d\.]+)')

        def _add_segment(start: float, end: float, raw_text_lines: List[str]) -> None:
            nonlocal last_cue_text
            if not raw_text_lines or start is None or end is None:
                return

            # Nettoyer et dédupliquer les lignes répétées au sein du même cue
            cleaned_lines = []
            for l in raw_text_lines:
                cl = clean_subtitle_text(l)
                if not cl:
                    continue
                if cleaned_lines and cl.startswith(cleaned_lines[-1]):
                    cleaned_lines[-1] = cl
                elif cleaned_lines and cleaned_lines[-1].startswith(cl):
                    continue
                elif cl not in cleaned_lines:
                    cleaned_lines.append(cl)

            raw_txt = " ".join(cleaned_lines)
            if not raw_txt:
                return

            full_txt = raw_txt

            # Déduplication à fenêtre roulante avec préservation du contexte multi-lignes
            if segments:
                # Contexte de comparaison : tester d'abord contre le texte complet du cue précédent
                # (préserve la fenêtre glissante YouTube à 3-5 lignes),
                # sinon repli sur le texte du dernier segment enregistré.
                prev_context = last_cue_text if last_cue_text else segments[-1]["text"]
                deduped = deduplicate_rolling_text(prev_context, raw_txt)

                # Si aucun chevauchement trouvé avec le cue précédent mais qu'il y en a avec le dernier segment
                if deduped == raw_txt and prev_context != segments[-1]["text"]:
                    deduped = deduplicate_rolling_text(segments[-1]["text"], raw_txt)

                if not deduped:
                    # Le cue actuel est un duplicata complet du précédent : prolonger sa durée
                    segments[-1]["end"] = max(segments[-1]["end"], end)
                    last_cue_text = raw_txt
                    return

                full_txt = deduped

            last_cue_text = raw_txt

            if full_txt:
                segments.append({
                    "start": start,
                    "end": end,
                    "text": full_txt
                })

        for line in lines:
            line_str = line.strip()
            match = time_pattern.search(line_str)
            if match:
                if current_start is not None and current_text:
                    _add_segment(current_start, current_end, current_text)
                current_start = parse_vtt_timestamp(match.group(1))
                current_end = parse_vtt_timestamp(match.group(2))
                current_text = []
            elif line_str and not line_str.startswith("WEBVTT") and not line_str.isdigit() and "-->" not in line_str:
                current_text.append(line_str)

        if current_start is not None and current_text:
            _add_segment(current_start, current_end, current_text)

        return segments

    def _transcribe_with_whisper(self, video_path: str) -> List[Dict[str, Any]]:
        # Extraire l'audio pour accélérer
        audio_path = video_path.rsplit(".", 1)[0] + "_temp.wav"
        extract_cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path
        ]
        subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        try:
            from faster_whisper import WhisperModel
            if self._whisper_model is None:
                self._whisper_model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

            whisper_segments, _ = self._whisper_model.transcribe(audio_path, language="fr")
            results = []
            for seg in whisper_segments:
                results.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip()
                })
            return results
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
