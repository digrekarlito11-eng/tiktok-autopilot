"""
Configuration des thèmes visuels et de l'habillage graphique pour Karl Studio.
Chaque thème définit les couleurs de la bannière Hook, des sous-titres,
du mot en surbrillance et de la barre de progression.
"""

from typing import Dict, Any

THEMES: Dict[str, Dict[str, Any]] = {
    "gospel": {
        "name": "Lumière Divine & Gospel (Or Céleste)",
        "hook_color": "&H0000D7FF&",       # Jaune or céleste
        "hook_outline": "&H00000000&",     # Contour net
        "sub_primary": "&H00FFFFFF&",      # Blanc pur
        "sub_highlight": "&H0000D7FF&",    # Or éclatant sur les mots forts (Dieu, Foi, Victoire)
        "progress_color": "0xFFD700",       # Barre dorée
        "font_name": "DejaVu Sans"
    },
    "gold": {
        "name": "Karl Studio Gold (Dark Luxury)",
        "hook_color": "&H0000D7FF&",       # Jaune or éclatant (format ASS BGR)
        "hook_outline": "&H00000000&",     # Contour noir profond
        "sub_primary": "&H00FFFFFF&",      # Blanc pur
        "sub_highlight": "&H0000D7FF&",    # Or vibrant pour le mot actif
        "progress_color": "0xFFD700",       # Couleur hex FFmpeg pour la barre de progression
        "font_name": "DejaVu Sans"
    },
    "neon": {
        "name": "Cyber Neon (Impact & Viralité)",
        "hook_color": "&H0000FF00&",       # Vert néon ultra dynamique
        "hook_outline": "&H00000000&",
        "sub_primary": "&H00FFFFFF&",
        "sub_highlight": "&H00FFFF00&",    # Cyan néon
        "progress_color": "0x00FF66",
        "font_name": "DejaVu Sans"
    },
    "minimal": {
        "name": "Cinematic Clean (Épuré)",
        "hook_color": "&H00FFFFFF&",       # Blanc pur cinéma
        "hook_outline": "&H00000000&",
        "sub_primary": "&H00E0E0E0&",
        "sub_highlight": "&H0000A5FF&",    # Orange discret
        "progress_color": "0xFFFFFF",
        "font_name": "DejaVu Sans"
    }
}

def get_theme(theme_name: str) -> Dict[str, Any]:
    return THEMES.get(theme_name.lower(), THEMES["gospel"])
