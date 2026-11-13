"""
Independent Forensic Verification Script
Milestone 2 Re-check (Auditor M2 Re-check)
"""

import os
import sys
import ast
import uuid
import tempfile
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path("/home/antigravity/digrekarlito11-eng/tiktok-autopilot")
sys.path.insert(0, str(PROJECT_ROOT))

from src.video_formatter import VideoFormatter, escape_ass_path_for_ffmpeg, clean_text_for_ass
from src.transcriber import VideoTranscriber, deduplicate_rolling_text
from src.clip_extractor import (
    ClipExtractor,
    normalize_french_word,
    stem_french_word,
    find_keyword_match,
    VIRAL_KEYWORDS
)


def log_check(name: str, passed: bool, details: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}: {details}")
    if not passed:
        raise AssertionError(f"Check failed: {name} - {details}")


def test_ast_anti_cheating():
    """Verify that source files do not contain cheat branches or test inspect tricks."""
    target_files = [
        PROJECT_ROOT / "src/video_formatter.py",
        PROJECT_ROOT / "src/transcriber.py",
        PROJECT_ROOT / "src/clip_extractor.py",
        PROJECT_ROOT / "src/downloader.py",
        PROJECT_ROOT / "src/tiktok_publisher.py",
        PROJECT_ROOT / "src/growth_optimizer.py"
    ]

    for file_path in target_files:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code, filename=str(file_path))

        # Check 1: No inspect or sys._getframe
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr in ("_getframe", "stack", "currentframe"):
                    log_check(f"AST inspect check on {file_path.name}", False, f"Forbidden attribute {node.attr}")
            if isinstance(node, ast.Compare):
                # Check for hardcoded test comparisons
                if isinstance(node.left, ast.Name):
                    for comparator in node.comparators:
                        if isinstance(comparator, ast.Constant):
                            val = str(comparator.value)
                            if val in ("Jésus-Christ", "Dieu-le-Père", "Saint-Esprit", "tiktok_l'onction_divine.mp4"):
                                log_check(f"Hardcoded check in {file_path.name}", False, f"Found hardcoded test literal {val}")

        log_check(f"AST anti-cheating check on {file_path.name}", True, "Zero inspection tricks or hardcoded test branches")


def test_video_formatter_ass_escaping_and_cleanup():
    """Test intermediate ASS file cleanup and path escaping under stress."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        formatter = VideoFormatter(output_dir=tmp_dir)

        # 1. Test escape_ass_path_for_ffmpeg with various dangerous paths
        cases = [
            ("/path/with/single'quote.ass", "'/path/with/singlequote.ass'"),
            ("/tmp/path/with/colons:and:slashes.ass", r"'/tmp/path/with/colons\:and\:slashes.ass'"),
            ("/path/with:colons.ass", r"'/path/with\:colons.ass'"),
            ("/path/'quote'and:colon.ass", r"'/path/quoteand\:colon.ass'"),
        ]
        for inp, expected in cases:
            out = escape_ass_path_for_ffmpeg(inp)
            log_check(f"escape_ass_path_for_ffmpeg('{inp}')", out == expected, f"Result: {out}")

        # 2. Test rendering with single quotes in filename
        # First generate a tiny 1-second synthetic video
        dummy_video = os.path.join(tmp_dir, "input.mp4")
        gen_cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=black:s=720x1280:d=1.5",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", "1.5", "-c:v", "libx264", "-c:a", "aac",
            dummy_video
        ]
        subprocess.run(gen_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        output_filename = "tiktok_l'onction_divine_test.mp4"
        segments = [{"start": 0.0, "end": 1.0, "text": "Dieu va faire des miracles"}]
        rendered_mp4 = formatter.render_tiktok_video(
            video_input=dummy_video,
            start_time=0.0,
            duration=1.0,
            hook_title="L'ONCTION DIVINE DANS TA VIE",
            segments=segments,
            output_filename=output_filename,
            watermark="@karlstudio",
            theme_name="gold",
            with_progress_bar=True
        )

        log_check("Render with single quotes in filename", os.path.exists(rendered_mp4), f"Output: {rendered_mp4}")

        # Verify resolution with ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0",
            rendered_mp4
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        w, h = res.stdout.strip().split(",")
        log_check("Rendered resolution 1080x1920", (int(w) == 1080 and int(h) == 1920), f"{w}x{h}")

        # Verify no temporary ASS files remain
        remaining_ass = [f for f in os.listdir(tmp_dir) if f.endswith(".ass")]
        log_check("Temporary ASS file cleanup on success", len(remaining_ass) == 0, f"Remaining: {remaining_ass}")

        # 3. Test cleanup on failure (try ... finally guarantee)
        try:
            formatter.render_tiktok_video(
                video_input="/nonexistent/path/corrupt_file.mp4",
                start_time=0.0,
                duration=1.0,
                hook_title="TEST CRASH",
                segments=segments,
                output_filename="crash_test.mp4",
                watermark="@karlstudio",
                theme_name="gold"
            )
        except Exception:
            pass  # Expected FFmpeg failure

        remaining_ass_after_crash = [f for f in os.listdir(tmp_dir) if f.endswith(".ass")]
        log_check("Temporary ASS file cleanup on FFmpeg exception", len(remaining_ass_after_crash) == 0, f"Remaining: {remaining_ass_after_crash}")


def test_transcriber_rolling_window_multi_line():
    """Verify rolling cue multi-line deduplication algorithm on 4+ cues."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        vtt_file = Path(tmp_dir) / "rolling_test.vtt"
        # 5-line rolling window over 4 successive cues
        content = """WEBVTT

00:00:00.000 --> 00:00:02.000
Ligne 1 de prédication
Ligne 2 de prophétie
Ligne 3 de prière
Ligne 4 de foi
Ligne 5 de miracle

00:00:02.000 --> 00:00:04.000
Ligne 2 de prophétie
Ligne 3 de prière
Ligne 4 de foi
Ligne 5 de miracle
Ligne 6 de délivrance

00:00:04.000 --> 00:00:06.000
Ligne 3 de prière
Ligne 4 de foi
Ligne 5 de miracle
Ligne 6 de délivrance
Ligne 7 de grâce

00:00:06.000 --> 00:00:08.000
Ligne 4 de foi
Ligne 5 de miracle
Ligne 6 de délivrance
Ligne 7 de grâce
Ligne 8 de bénédiction
"""
        vtt_file.write_text(content, encoding="utf-8")
        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(str(vtt_file))

        full_transcript = " ".join(s["text"] for s in segments)

        # Check each line count
        for i in range(1, 9):
            line_pattern = f"Ligne {i} de"
            count = full_transcript.count(line_pattern)
            log_check(f"Rolling deduplication: '{line_pattern}' appears exactly once", count == 1, f"Found {count} times")

        log_check("Segments length matches cue delta emission", len(segments) == 4, f"Segments: {len(segments)}")


def test_french_nlp_compound_and_punctuation():
    """Verify French NLP keyword matching on compound biblical terms and dialogue punctuation."""
    # 1. Hyphenated compound biblical terms
    test_compounds = [
        ("Jésus-Christ", 3.5, "jésus"),
        ("Dieu-le-Père", 3.5, "dieu"),
        ("Saint-Esprit", 3.5, "esprit"),
        ("Père-Éternel", 3.5, "éternel"),
        ("L'Éternel-Dieu", 3.5, "éternel"),
        ("Christ-Sauveur", 3.5, "christ"),
    ]
    for raw, expected_score, expected_kw in test_compounds:
        score, kw = find_keyword_match(raw)
        log_check(f"Compound term matching '{raw}'", (score == expected_score and kw == expected_kw), f"Got ({score}, {kw})")

    # 2. Dialogue punctuation stripping
    dialogue_cases = [
        ("-l'onction", 3.5, "onction"),
        ("«l'onction»", 3.5, "onction"),
        ("(l'onction)", 3.5, "onction"),
        ("—d'éternel", 3.5, "éternel"),
        ("[qu'éternel]", 3.5, "éternel"),
        ("«d'onctions»", 3.5, "onctions"),
        ("\"bénédictions!\"", 3.5, "bénédictions"),
        ("...prières?", 3.5, "prières"),
    ]
    for raw, expected_score, expected_kw in dialogue_cases:
        score, kw = find_keyword_match(raw)
        log_check(f"Dialogue punctuation stripping '{raw}'", (score == expected_score and kw == expected_kw), f"Got ({score}, {kw})")

    # 3. Non-keyword compound terms return 0.0
    score, kw = find_keyword_match("Jean-Baptiste")
    log_check("Non-keyword compound 'Jean-Baptiste' returns 0.0", score == 0.0 and kw is None, f"Got ({score}, {kw})")

    # 4. General normalizer logic on arbitrary words
    res_norm = normalize_french_word("«d'abidjan»")
    log_check("normalize_french_word('«d\'abidjan»')", res_norm == "abidjan", f"Got: {res_norm}")
    res_stem = stem_french_word("tableaux")
    log_check("stem_french_word('tableaux')", res_stem == "tableau", f"Got: {res_stem}")


def main():
    print("=" * 60)
    print("STARTING INDEPENDENT FORENSIC VERIFICATION AUDIT (M2 RE-CHECK)")
    print("=" * 60)

    test_ast_anti_cheating()
    test_video_formatter_ass_escaping_and_cleanup()
    test_transcriber_rolling_window_multi_line()
    test_french_nlp_compound_and_punctuation()

    print("=" * 60)
    print("ALL INDEPENDENT FORENSIC AUDIT CHECKS PASSED: VERDICT = CLEAN")
    print("=" * 60)


if __name__ == "__main__":
    main()
