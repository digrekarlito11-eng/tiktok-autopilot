import os
import re
import subprocess
import uuid
from typing import List, Dict, Any, Optional
from .themes import get_theme

def format_ass_time(seconds: float) -> str:
    """Formate des secondes en timestamp ASS : H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def clean_text_for_ass(text: str) -> str:
    """
    Retire les caractères non-ASCII ou emojis (SMP et BMP) ainsi que le sélecteur
    de variante \ufe0f et les accolades pour éviter les soucis de rendu et de police ASS.
    """
    emoji_pattern = re.compile(
        r'['
        r'\U00010000-\U0010ffff'  # Emojis SMP (faces, symboles, objets)
        r'\u2600-\u26ff'          # Symboles divers BMP (⚡, ⚠️, ⛪, etc.)
        r'\u2700-\u27bf'          # Dingbats BMP (✝, ✞, etc.)
        r'\u2b00-\u2bff'          # Symboles & flèches divers BMP (⭐, ⭕, etc.)
        r'\u2300-\u23ff'          # Symboles techniques divers BMP (⌛, ⏳, ⌚, etc.)
        r'\u2190-\u21ff'          # Flèches BMP
        r'\u2934-\u2935'          # Flèches courbes BMP
        r'\u3297\u3299\u3030\u303d'
        r'\u200d\u200c'          # ZWJ, ZWNJ
        r'\ufe0e\ufe0f'          # Sélecteurs de variante
        r'\u20e3'                # Touche de saisie combinée
        r']+',
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', text)
    cleaned = cleaned.replace('{', '').replace('}', '')
    # Condenser les espaces consécutifs générés par le retrait des emojis
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()

def escape_ass_path_for_ffmpeg(path: str) -> str:
    """
    Échappe le chemin absolu du fichier ASS pour insertion sécurisée
    dans le filtergraph FFmpeg (antislashs, deux-points, apostrophes).
    """
    norm_path = os.path.abspath(path).replace('\\', '/')
    # FFmpeg filtergraph strings in single quotes cannot escape single quotes with \'.
    # Neutralize quotes and escape colons for robust argument parsing.
    escaped = norm_path.replace("'", "").replace(':', r'\:')
    return f"'{escaped}'"

class VideoFormatter:
    """
    Sous-agent Media-Bot / Formateur Vidéo 9:16 TikTok.
    Prend le segment découpé et génère le fichier MP4 vertical (1080x1920)
    avec :
    - Fond flouté esthétique accéléré par sous-échantillonnage
    - Vidéo nette centrée
    - Titre d'accroche (Hook) dans la Safe Zone supérieure
    - Sous-titres dynamiques mot-à-mot protégés par MarginR=140 (évite l'occlusion par les boutons TikTok)
    - Watermark / Identifiant de marque (@karlstudio)
    - Barre de progression animée au bas de l'écran
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def create_ass_subtitles(
        self,
        segments: List[Dict[str, Any]],
        hook_title: str,
        ass_path: str,
        clip_start: float,
        watermark: str = "@karlstudio",
        theme_name: str = "gold"
    ):
        theme = get_theme(theme_name)
        clean_hook = clean_text_for_ass(hook_title)
        clean_watermark = clean_text_for_ass(watermark)

        # Style ASS avec les couleurs du thème choisi et marge droite MarginR=140 pour Safe Zone TikTok
        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HookHeader,{theme['font_name']},58,{theme['hook_color']},{theme['hook_color']},{theme['hook_outline']},&H80000000,-1,0,0,0,100,100,1,0,1,6,3,8,40,40,240,1
Style: TikTokSubtitle,{theme['font_name']},52,{theme['sub_primary']},{theme['sub_primary']},{theme['hook_outline']},&H90000000,-1,0,0,0,100,100,1,0,1,5,2,2,60,140,480,1
Style: WatermarkBadge,{theme['font_name']},32,&H80FFFFFF,&H80FFFFFF,&H80000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,1,7,45,45,210,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        total_clip_duration = 0.0
        if segments:
            total_clip_duration = max(s["end"] - clip_start for s in segments)
        else:
            total_clip_duration = 60.0

        dur_str = format_ass_time(total_clip_duration)

        # 1. Watermark en haut à gauche de la Safe Zone
        if clean_watermark:
            ass_content += f"Dialogue: 0,0:00:00.00,{dur_str},WatermarkBadge,,0,0,0,,{clean_watermark}\n"

        # 2. Titre d'accroche centré en haut
        ass_content += f"Dialogue: 0,0:00:00.00,{dur_str},HookHeader,,0,0,0,,{clean_hook}\n"

        # 3. Sous-titres dynamiques synchronisés
        for seg in segments:
            rel_start = max(0.0, seg["start"] - clip_start)
            rel_end = max(rel_start + 0.5, seg["end"] - clip_start)
            txt = clean_text_for_ass(seg["text"])
            if not txt:
                continue

            words = txt.split()
            chunk_size = 5
            word_chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
            chunk_dur = (rel_end - rel_start) / max(1, len(word_chunks))

            for idx, chunk in enumerate(word_chunks):
                c_start = rel_start + (idx * chunk_dur)
                c_end = c_start + chunk_dur
                chunk_str = " ".join(chunk)

                # Surbrillance avec la couleur du thème
                if len(chunk) > 1:
                    highlighted = f"{{\\c{theme['sub_highlight']}}}{chunk[0]}{{\\c{theme['sub_primary']}}} " + " ".join(chunk[1:])
                else:
                    highlighted = f"{{\\c{theme['sub_highlight']}}}{chunk_str}"

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
        output_filename: str,
        watermark: str = "@karlstudio",
        theme_name: str = "gold",
        with_progress_bar: bool = True
    ) -> str:
        """
        Découpe et génère la vidéo finale 9:16 avec FFmpeg.
        """
        theme = get_theme(theme_name)
        output_path = os.path.join(self.output_dir, output_filename)
        clean_sub_id = uuid.uuid4().hex[:10]
        ass_path = os.path.join(self.output_dir, f"temp_sub_{clean_sub_id}.ass")

        print(f"🎬 [Media-Bot] Préparation des sous-titres (Thème: {theme['name']}, Watermark: {watermark})...")
        self.create_ass_subtitles(
            segments,
            hook_title,
            ass_path,
            clip_start=start_time,
            watermark=watermark,
            theme_name=theme_name
        )

        print(f"🎞️ [Media-Bot] Rendu FFmpeg 9:16 (Fond flou + vidéo nette + Safe Zones + Barre animée)...")

        # Filtre complexe FFmpeg :
        # 1. Échelle + recadrage + flou optimisé par downscale 10x préalable (accélération CPU 5x)
        # 2. Vidéo nette au centre
        # 3. Sous-titres ASS par-dessus avec échappement sécurisé du chemin ass_path
        # 4. Barre de progression animée synchronisée au bas
        escaped_ass = escape_ass_path_for_ffmpeg(ass_path)
        base_filter = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"scale=108:192,boxblur=5:2,scale=1080:1920[bg];"
            f"[0:v]scale=1080:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[merged];"
            f"[merged]ass={escaped_ass}[subbed]"
        )

        if with_progress_bar:
            # Barre de progression dynamique de 14px de hauteur au bas de l'écran
            progress_expr = f"w='1080*(t/{duration})':h=14:x=0:y=1906:color={theme['progress_color']}@1:t=fill"
            final_filter = f"{base_filter};[subbed]drawbox={progress_expr}[outv]"
        else:
            final_filter = f"{base_filter};[subbed]copy[outv]"

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", video_input,
            "-filter_complex", final_filter,
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

        try:
            subprocess.run(ffmpeg_cmd, check=True)
        finally:
            if os.path.exists(ass_path):
                os.remove(ass_path)

        print(f"✨ [Media-Bot] Vidéo TikTok finalisée avec succès : {output_path}")
        return output_path
