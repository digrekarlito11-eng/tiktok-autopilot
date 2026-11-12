import os
import re
import subprocess
from typing import List, Dict, Any, Optional

def format_ass_time(seconds: float) -> str:
    """Formate des secondes en timestamp ASS : H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def clean_text_for_ass(text: str) -> str:
    """Retire les caractères non-ASCII ou emojis pour éviter les soucis de police système."""
    # Retirer les emojis simples
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    # Échapper les accolades ASS
    text = text.replace('{', '').replace('}', '')
    return text.strip()

class VideoFormatter:
    """
    Sous-agent Media-Bot / Formateur Vidéo 9:16 TikTok.
    Prend le segment découpé et génère le fichier MP4 vertical (1080x1920)
    avec fond flouté esthétique, titre d'accroche et sous-titres dynamiques.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def create_ass_subtitles(self, segments: List[Dict[str, Any]], hook_title: str, ass_path: str, clip_start: float):
        """
        Crée un fichier de sous-titres ASS avec styles TikTok Safe-Zone :
        - HookHeader en haut (bannière jaune vif avec ombre)
        - TikTokSubtitle au centre-bas (texte blanc avec contour noir net)
        """
        clean_hook = clean_text_for_ass(hook_title)

        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HookHeader,DejaVu Sans,58,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,6,3,8,40,40,240,1
Style: TikTokSubtitle,DejaVu Sans,52,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,5,2,2,60,60,480,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        total_clip_duration = 0.0
        if segments:
            total_clip_duration = max(s["end"] - clip_start for s in segments)
        else:
            total_clip_duration = 60.0

        # Affichage du titre d'accroche sur toute la durée du clip
        ass_content += f"Dialogue: 0,0:00:00.00,{format_ass_time(total_clip_duration)},HookHeader,,0,0,0,,{clean_hook}\n"

        # Ajout des dialogues avec horodatages relatifs
        for seg in segments:
            rel_start = max(0.0, seg["start"] - clip_start)
            rel_end = max(rel_start + 0.5, seg["end"] - clip_start)
            txt = clean_text_for_ass(seg["text"])
            if not txt:
                continue

            # Découper en sous-phrases de 4-6 mots maximum pour l'effet dynamique TikTok
            words = txt.split()
            chunk_size = 5
            word_chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
            chunk_dur = (rel_end - rel_start) / max(1, len(word_chunks))

            for idx, chunk in enumerate(word_chunks):
                c_start = rel_start + (idx * chunk_dur)
                c_end = c_start + chunk_dur
                chunk_str = " ".join(chunk)
                
                # Mettre en valeur le premier mot en couleur accentuée
                highlighted = r"{\c&H00D7FF&}" + chunk[0] + r"{\c&HFFFFFF&} " + " ".join(chunk[1:]) if len(chunk) > 1 else chunk_str
                ass_content += f"Dialogue: 1,{format_ass_time(c_start)},{format_ass_time(c_end)},TikTokSubtitle,,0,0,0,,{highlighted}\n"

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

    def render_tiktok_video(
        self,
        video_input: str,
        start_time: float,
        duration: float,
        hook_title: str,
        segments: List[Dict[str, Any]],
        output_filename: str
    ) -> str:
        """
        Découpe et génère la vidéo finale 9:16 avec FFmpeg.
        """
        output_path = os.path.join(self.output_dir, output_filename)
        ass_path = os.path.join(self.output_dir, "temp_subtitles.ass")

        print(f"🎬 [Media-Bot] Génération des sous-titres stylisés TikTok...")
        self.create_ass_subtitles(segments, hook_title, ass_path, clip_start=start_time)

        print(f"🎞️ [Media-Bot] Rendu FFmpeg 9:16 (fond flou + vidéo nette + safe zones)...")

        # Filtre complexe FFmpeg :
        # 1. Échelle + recadrage + flou lourd pour le fond 9:16 (1080x1920)
        # 2. Vidéo nette au premier plan centrée horizontalement et verticalement
        # 3. Application des sous-titres ASS par-dessus
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
            f"[0:v]scale=1080:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[merged];"
            f"[merged]ass={ass_path}[outv]"
        )

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", video_input,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            output_path
        ]

        subprocess.run(ffmpeg_cmd, check=True)

        if os.path.exists(ass_path):
            os.remove(ass_path)

        print(f"✨ [Media-Bot] Vidéo TikTok finalisée avec succès : {output_path}")
        return output_path
