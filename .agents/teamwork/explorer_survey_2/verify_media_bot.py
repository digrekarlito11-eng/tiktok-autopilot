import sys
import os
import re

# Add src to path
sys.path.insert(0, "/home/antigravity/digrekarlito11-eng/tiktok-autopilot")

from src.transcriber import VideoTranscriber, parse_vtt_timestamp, clean_subtitle_text
from src.clip_extractor import ClipExtractor, VIRAL_KEYWORDS
from src.themes import get_theme, THEMES
from src.video_formatter import VideoFormatter, format_ass_time, clean_text_for_ass

print("=== 1. Testing parse_vtt_timestamp ===")
print("00:01:23.456 ->", parse_vtt_timestamp("00:01:23.456"))
print("01:23.456 ->", parse_vtt_timestamp("01:23.456"))
print("23.456 ->", parse_vtt_timestamp("23.456"))

print("\n=== 2. Testing YouTube Auto-Generated VTT parsing ===")
# Typical YouTube auto-generated VTT snippet with rolling cues and inline timestamp tags
yt_vtt_sample = """WEBVTT
Kind: captions
Language: fr

00:00:01.000 --> 00:00:03.500 align:start position:0%
Dieu va faire<00:00:01.800><c> un miracle</c>

00:00:03.500 --> 00:00:06.000 align:start position:0%
Dieu va faire un miracle
dans ta vie<00:00:04.500><c> reçois</c>

00:00:06.000 --> 00:00:09.000 align:start position:0%
dans ta vie reçois
cette bénédiction<00:00:07.500><c> aujourd'hui</c>
"""

tmp_vtt = "/home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/explorer_survey_2/test_yt.vtt"
with open(tmp_vtt, "w", encoding="utf-8") as f:
    f.write(yt_vtt_sample)

transcriber = VideoTranscriber()
segments = transcriber._parse_vtt(tmp_vtt)
print("Parsed segments count:", len(segments))
for s in segments:
    print(f"[{s['start']}s -> {s['end']}s]: '{s['text']}'")

print("\n=== 3. Testing Keyword Matching (Plurals & Accents) ===")
test_phrases = [
    "Dieu va faire des miracles dans ta vie",
    "Reçois toutes ces bénédictions prophétiques",
    "L'Éternel est mon berger",
    "C'est l'onction de Dieu",
    "Voici le secret"
]

extractor = ClipExtractor()
for phrase in test_phrases:
    score = 0
    words = phrase.lower().split()
    matched = []
    for w in words:
        clean_w = "".join(c for c in w if c.isalpha())
        if clean_w in VIRAL_KEYWORDS:
            score += VIRAL_KEYWORDS[clean_w]
            matched.append(clean_w)
    print(f"Phrase: '{phrase}' -> Matched: {matched}, Score: {score}")

print("\n=== 4. Testing Emoji & Special Characters in ASS Subtitles ===")
test_titles = [
    "DIEU A UN MESSAGE POUR TOI 🕊️",
    "TA VICTOIRE EST PROCHE ⚔️",
    "LE MIRACLE ARRIVE ⚡",
    "FAIS CETTE PRIÈRE 🙏",
    "L'HEURE DE DIEU : C'EST MAINTENANT !"
]
for t in test_titles:
    cleaned = clean_text_for_ass(t)
    print(f"Original: '{t}' -> Cleaned: '{cleaned}'")

print("\n=== 5. Testing Themes ===")
for name in ["gospel", "gold", "neon", "minimal", "unknown"]:
    th = get_theme(name)
    print(f"Theme '{name}': name='{th['name']}', hook={th['hook_color']}, progress={th['progress_color']}")
