"""
tests/test_adversarial_media_bot.py - Empirical Adversarial Test Harness for Media-Bot (Milestone 2).

Designed by Challenger 1 to stress-test:
1. French NLP: apostrophes, elisions, plurals, non-breaking spaces, hyphenated terms, dialogue dashes.
2. VTT rolling deduplication: 5-line rolling cues, single-word rolling, identical timestamps, intra-cue duplicates.
3. VideoFormatter ASS escaping & FFmpeg rendering: video titles with spaces, colons, quotes, accents, brackets.
"""

import os
import sys
import subprocess
import pytest
from typing import List, Dict, Any

from src.clip_extractor import (
    ClipExtractor,
    VIRAL_KEYWORDS,
    normalize_french_word,
    stem_french_word,
    find_keyword_match,
)
from src.transcriber import (
    VideoTranscriber,
    parse_vtt_timestamp,
    clean_subtitle_text,
    deduplicate_rolling_text,
)
from src.video_formatter import (
    VideoFormatter,
    clean_text_for_ass,
    escape_ass_path_for_ffmpeg,
    format_ass_time,
)


# ============================================================================
# 1. ADVERSARIAL: French NLP (Elisions, Plurals, Accents, Hyphens, Punctuation)
# ============================================================================

class TestFrenchNLPRobustnessAndVulnerabilities:
    """Empirical tests for French NLP keyword matching."""

    @pytest.mark.parametrize("input_word,expected_stem", [
        ("miracles", "miracle"),
        ("combats", "combat"),
        ("prières", "prière"),
        ("bénédictions", "bénédiction"),
        ("victoires", "victoire"),
        ("onctions", "onction"),
        ("prophéties", "prophétie"),
        ("foi", "foi"),
        ("dieu", "dieu"),
    ])
    def test_stem_french_word_edge_cases(self, input_word, expected_stem):
        assert stem_french_word(input_word) == expected_stem

    @pytest.mark.parametrize("word,expected_score,expected_kw", [
        ("l'onction", 3.5, "onction"),
        ("l’onction", 3.5, "onction"),
        ("d'onctions", 3.5, "onctions"),
        ("d’onctions", 3.5, "onctions"),
        ("l'éternel", 3.5, "éternel"),
        ("l’éternel", 3.5, "éternel"),
        ("d'éternel", 3.5, "éternel"),
        ("qu'éternel", 3.5, "éternel"),
        ("c'est", 0.0, None),
        ("ÉTERNEL", 3.5, "éternel"),
        ("ETERNEL", 3.5, "eternel"),
        ("L’ÉTERNEL", 3.5, "éternel"),
        ("L'ÉTERNEL", 3.5, "éternel"),
        ("D'ONCTIONS", 3.5, "onctions"),
        ("BÉNÉDICTION", 3.5, "bénédiction"),
        ("BÉNÉDICTIONS", 3.5, "bénédictions"),
        ("PRIÈRE", 3.5, "prière"),
        ("PRIÈRES", 3.5, "prières"),
        ("DÉLIVRANCE", 4.0, "délivrance"),
        ("GRÂCE", 3.0, "grâce"),
        ("PROPHÉTIE", 4.0, "prophétie"),
        ("JÉSUS", 3.5, "jésus"),
        ("JESUS", 3.5, "jesus"),
    ])
    def test_find_keyword_match_apostrophes_and_all_caps(self, word, expected_score, expected_kw):
        score, kw = find_keyword_match(word)
        assert score == expected_score
        if expected_kw:
            assert kw == expected_kw

    def test_non_breaking_spaces_in_clip_text(self):
        """Non-breaking spaces (U+00A0 and narrow U+202F) must not prevent keyword detection."""
        extractor = ClipExtractor(min_duration=10.0, max_duration=40.0)
        text = "Voici\u00a0! Dieu va libérer\u202fl'onction divine et des\u00a0miracles\u202f!"
        segments = [{"start": 0.0, "end": 26.0, "text": text}]
        clips = extractor.find_best_clips(segments, top_k=1)
        assert len(clips) == 1
        clip = clips[0]
        assert clip["score"] > 0
        matched = clip["matched_keywords"]
        assert any("onction" in k for k in matched)
        assert any("miracle" in k for k in matched)
        assert any("dieu" in k for k in matched)

    def test_vulnerability_hyphenated_biblical_terms_missed(self):
        """
        REMEDIATION VERIFICATION:
        Terms like 'Jésus-Christ', 'Dieu-le-Père', and 'Saint-Esprit' now match
        their core theological keywords because hyphens are tokenized and scored.
        """
        score_jc, kw_jc = find_keyword_match("Jésus-Christ")
        score_dp, kw_dp = find_keyword_match("Dieu-le-Père")
        score_se, kw_se = find_keyword_match("Saint-Esprit")

        assert score_jc == 3.5, f"Expected 3.5 for Jésus-Christ, got {score_jc}"
        assert kw_jc == "jésus"
        assert score_dp == 3.5, f"Expected 3.5 for Dieu-le-Père, got {score_dp}"
        assert kw_dp == "dieu"
        assert score_se == 3.5, f"Expected 3.5 for Saint-Esprit, got {score_se}"
        assert kw_se == "esprit"

    def test_vulnerability_leading_punctuation_breaks_elision(self):
        """
        REMEDIATION VERIFICATION:
        Leading dialogue dashes (-), guillemets («), parentheses ((), and quotes (“)
        are cleanly stripped prior to elision normalization so that French keywords
        like l'onction retain their full viral score.
        """
        score_dash, kw_dash = find_keyword_match("-l'onction")
        score_guill, kw_guill = find_keyword_match("«l'onction»")
        score_paren, kw_paren = find_keyword_match("(l'onction)")

        assert score_dash == 3.5, f"Expected 3.5 for -l'onction, got {score_dash}"
        assert kw_dash == "onction"
        assert score_guill == 3.5, f"Expected 3.5 for «l'onction», got {score_guill}"
        assert kw_guill == "onction"
        assert score_paren == 3.5, f"Expected 3.5 for (l'onction), got {score_paren}"
        assert kw_paren == "onction"


# ============================================================================
# 2. ADVERSARIAL: Pathological VTT Rolling Deduplication
# ============================================================================

class TestPathologicalVTTDeduplicationVulnerabilities:
    """Stress tests for VTT parsing with pathological rolling windows."""

    def test_identical_timestamps_repeated_cues(self, tmp_path):
        """Identical text cues at same timestamps are properly collapsed."""
        vtt_file = tmp_path / "identical_timestamps.vtt"
        content = """WEBVTT

00:00:05.000 --> 00:00:08.000
Recevez la paix du Seigneur

00:00:05.000 --> 00:00:08.000
Recevez la paix du Seigneur

00:00:08.000 --> 00:00:10.000
Et marchez dans la foi
"""
        vtt_file.write_text(content, encoding="utf-8")
        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(str(vtt_file))

        assert len(segments) == 2
        assert segments[0]["text"] == "Recevez la paix du Seigneur"
        assert segments[1]["text"] == "Et marchez dans la foi"

    def test_zero_duration_and_empty_cues(self, tmp_path):
        """Cues with zero duration or empty/whitespace text."""
        vtt_file = tmp_path / "zero_empty.vtt"
        content = """WEBVTT

00:00:01.000 --> 00:00:01.000
Flash cue

00:00:02.000 --> 00:00:04.000
   

00:00:04.000 --> 00:00:06.000
[Applaudissements]

00:00:06.000 --> 00:00:09.000
Parole puissante
"""
        vtt_file.write_text(content, encoding="utf-8")
        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(str(vtt_file))

        texts = [s["text"] for s in segments]
        assert "Parole puissante" in texts
        assert not any(t == "" for t in texts)
        assert not any("Applaudissements" in t for t in texts)

    def test_intra_cue_repetitive_lines(self, tmp_path):
        """Intra-cue repeated lines (4 copies of same line in 1 cue)."""
        vtt_file = tmp_path / "intra_cue_repeat.vtt"
        content = """WEBVTT

00:00:01.000 --> 00:00:05.000
Jésus est le même hier, aujourd'hui et éternellement
Jésus est le même hier, aujourd'hui et éternellement
Jésus est le même hier, aujourd'hui et éternellement
"""
        vtt_file.write_text(content, encoding="utf-8")
        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(str(vtt_file))

        assert len(segments) == 1
        assert segments[0]["text"] == "Jésus est le même hier, aujourd'hui et éternellement"

    def test_vulnerability_multi_line_rolling_window_fails_after_first_cue(self, tmp_path):
        """
        REMEDIATION VERIFICATION:
        In a 5-line rolling window WebVTT caption sequence, context is preserved
        across successive cues so that lines are never duplicated in the parsed transcript.
        """
        vtt_file = tmp_path / "5_line_rolling_defect.vtt"
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
"""
        vtt_file.write_text(content, encoding="utf-8")
        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(str(vtt_file))

        full_transcript = " ".join(s["text"] for s in segments)
        # Remediated: "Ligne 3 de prière" appears EXACTLY ONCE (no duplication!)
        duplication_count = full_transcript.count("Ligne 3 de prière")
        assert duplication_count == 1, f"Expected 1 occurrence, got {duplication_count}"

    def test_single_word_rolling_cues(self, tmp_path):
        """Simulates word-by-word rolling captions across cues."""
        vtt_file = tmp_path / "word_by_word.vtt"
        content = """WEBVTT

00:00:01.000 --> 00:00:02.000
Dieu

00:00:02.000 --> 00:00:03.000
Dieu va

00:00:03.000 --> 00:00:04.000
va agir
"""
        vtt_file.write_text(content, encoding="utf-8")
        transcriber = VideoTranscriber()
        segments = transcriber._parse_vtt(str(vtt_file))
        assert len(segments) == 3
        assert segments[0]["text"] == "Dieu"
        assert segments[1]["text"] == "va"
        assert segments[2]["text"] == "agir"


# ============================================================================
# 3. ADVERSARIAL: ASS Filtergraph Escaping & FFmpeg Rendering
# ============================================================================

class TestVideoFormatterFiltergraphEscapingVulnerabilities:
    """Stress tests for ASS file generation, escaping, and FFmpeg filtergraph execution."""

    @pytest.mark.parametrize("hook_title,expected_clean", [
        (
            'ÉCOUTE CE MESSAGE: DIEU DIT "TU ES VAINQUEUR" !',
            'ÉCOUTE CE MESSAGE: DIEU DIT "TU ES VAINQUEUR" !'
        ),
        (
            "L'ÉTERNEL VA AGIR {TAG_INJECTION} MAINTENANT 🕊️⚡✝️⚠️⭐",
            "L'ÉTERNEL VA AGIR TAG_INJECTION MAINTENANT"
        ),
        (
            "   Multi-space    and    tabs\t\net \nnewlines   ",
            "Multi-space and tabs et newlines"
        ),
    ])
    def test_clean_text_for_ass_complex_titles(self, hook_title, expected_clean):
        cleaned = clean_text_for_ass(hook_title)
        assert cleaned == expected_clean

    def test_vulnerability_single_quote_in_filename_crashes_ffmpeg(
        self, synthetic_preaching_video, sample_preaching_segments, tmp_path
    ):
        """
        REMEDIATION VERIFICATION:
        Filenames containing single quotes (e.g. 'tiktok_l\'onction_divine.mp4')
        now render smoothly without FFmpeg filtergraph syntax crashes because
        the intermediate ASS path is sanitized (temp_sub_{id}.ass) and escape_ass_path_for_ffmpeg
        safely handles quotes.
        """
        formatter = VideoFormatter(output_dir=str(tmp_path))
        filename_with_quote = "tiktok_l'onction_divine.mp4"

        final_mp4 = formatter.render_tiktok_video(
            video_input=synthetic_preaching_video,
            start_time=0.0,
            duration=2.0,
            hook_title="L'ONCTION DE DIEU",
            segments=sample_preaching_segments[:1],
            output_filename=filename_with_quote,
            watermark="@karlstudio",
            theme_name="gold",
            with_progress_bar=True
        )

        assert os.path.exists(final_mp4)
        assert os.path.getsize(final_mp4) > 1000

        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            final_mp4
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        w, h = res.stdout.strip().split(",")
        assert int(w) == 1080
        assert int(h) == 1920

    def test_ffmpeg_rendering_with_spaces_colons_and_accents_succeeds(
        self, synthetic_preaching_video, sample_preaching_segments, tmp_path
    ):
        """
        Verifies that when titles do NOT contain single quotes,
        spaces, colons, brackets, and French accents succeed cleanly.
        """
        complex_out_dir = tmp_path / "rendu vidéo avec espaces"
        complex_out_dir.mkdir(parents=True, exist_ok=True)
        formatter = VideoFormatter(output_dir=str(complex_out_dir))

        # Colons, spaces, brackets, French accents (no single quotes)
        safe_complex_filename = "tiktok_Pasteur Jean: Miracle & Foi [Côte d Ivoire].mp4"
        complex_hook = 'ÉCOUTE CE MESSAGE: "DIEU VA AGIR" ! 🕊️⚡ {MIRACLE}'

        final_mp4 = formatter.render_tiktok_video(
            video_input=synthetic_preaching_video,
            start_time=0.0,
            duration=2.0,
            hook_title=complex_hook,
            segments=sample_preaching_segments[:2],
            output_filename=safe_complex_filename,
            watermark="@karlstudio: officiel",
            theme_name="gospel",
            with_progress_bar=True
        )

        assert os.path.exists(final_mp4)
        assert os.path.getsize(final_mp4) > 1000

        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "csv=p=0",
            final_mp4
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        w, h, dur = res.stdout.strip().split(",")
        assert int(w) == 1080
        assert int(h) == 1920
        assert float(dur) >= 1.9
