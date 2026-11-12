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

        time_pattern = re.compile(r'(\d+:\d+:[\d\.]+|\d+:[\d\.]+)\s*-->\s*(\d+:\d+:[\d\.]+|\d+:[\d\.]+)')

        for line in lines:
            line_str = line.strip()
            match = time_pattern.search(line_str)
            if match:
                if current_start is not None and current_text:
                    full_txt = clean_subtitle_text(" ".join(current_text))
                    if full_txt:
                        segments.append({
                            "start": current_start,
                            "end": current_end,
                            "text": full_txt
                        })
                current_start = parse_vtt_timestamp(match.group(1))
                current_end = parse_vtt_timestamp(match.group(2))
                current_text = []
            elif line_str and not line_str.startswith("WEBVTT") and not line_str.isdigit() and "-->" not in line_str:
                current_text.append(line_str)

        if current_start is not None and current_text:
            full_txt = clean_subtitle_text(" ".join(current_text))
            if full_txt:
                segments.append({
                    "start": current_start,
                    "end": current_end,
                    "text": full_txt
                })

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
