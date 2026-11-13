# Handoff Report — Challenger 1 (Milestone 2: Media-Bot Pipeline Hardening)

**Timestamp**: 2026-11-12T19:59:00Z  
**Agent**: Challenger 1 (`challenger_m2_1`)  
**Parent Agent**: `0b15047f2814c727611000b3f1df5d16`  
**Milestone**: M2 (Media-Bot Pipeline Hardening)  
**Verdict**: **`REQUEST_CHANGES`**  

---

## 1. Observation

Direct observations and empirical execution results obtained by writing and running the adversarial test suite `tests/test_adversarial_media_bot.py`:

1. **FFmpeg ASS Filter Crash on Single Quotes in Filenames (`src/video_formatter.py`)**:
   - In `src/video_formatter.py`, lines 41-48:
     ```python
     def escape_ass_path_for_ffmpeg(path: str) -> str:
         norm_path = os.path.abspath(path).replace('\\', '/')
         escaped = norm_path.replace("'", r"\'").replace(':', r'\:')
         return f"'{escaped}'"
     ```
   - In `src/video_formatter.py`, lines 157 & 182:
     ```python
     ass_path = os.path.join(self.output_dir, f"temp_{output_filename}.ass")
     ...
     escaped_ass = escape_ass_path_for_ffmpeg(ass_path)
     base_filter = (
         ...
         f"[merged]ass={escaped_ass}[subbed]"
     )
     ```
   - When an `output_filename` contains a single quote or apostrophe (e.g. `tiktok_l'onction_divine.mp4` or titles referencing `Côte d'Ivoire`), `escape_ass_path_for_ffmpeg` produces `'/.../temp_tiktok_l\'onction_divine.mp4.ass'`.
   - Running FFmpeg with this filter argument fails with:
     ```
     [Parsed_ass_0 @ 0x...] ass_read_file(/.../temp_tiktok_lonction_divine.mp4.ass[subbed]): fopen failed
     [AVFilterGraph @ 0x...] Error initializing filter 'ass' with args '/.../temp_tiktok_l\onction_divine.mp4.ass[subbed]'
     Error initializing complex filters.
     Invalid argument
     ```
     and Python raises `subprocess.CalledProcessError: Command '['ffmpeg', ...]' returned non-zero exit status 1`.
   - Confirmed by `test_vulnerability_single_quote_in_filename_crashes_ffmpeg` in `tests/test_adversarial_media_bot.py`.

2. **Multi-line Rolling Window WebVTT Deduplication Loss (`src/transcriber.py`)**:
   - In `src/transcriber.py`, lines 109-117:
     ```python
     if segments:
         prev_seg = segments[-1]
         deduped = deduplicate_rolling_text(prev_seg["text"], full_txt)
         if not deduped:
             prev_seg["end"] = max(prev_seg["end"], end)
             return
         full_txt = deduped
     ```
   - In progressive rolling subtitles (such as 5-line rolling WebVTT from YouTube auto-subs), Cue 1 emits lines 1-5, which are stored in `segments[0]`.
   - Cue 2 emits lines 2-6. Overlap with Cue 1 is detected, so lines 2-5 are trimmed; only line 6 is saved as `segments[1]["text"]`.
   - Cue 3 emits lines 3-7. It compares `full_txt` against `segments[-1]["text"]`, which contains ONLY line 6.
   - Because Cue 3 begins with line 3 (not line 6), `deduplicate_rolling_text` finds 0 prefix/suffix overlap.
   - Cue 3 is appended in full (`"Ligne 3 de prière Ligne 4 ... Ligne 7"`), duplicating lines 3, 4, 5, and 6.
   - Empirically confirmed in `test_vulnerability_multi_line_rolling_window_fails_after_first_cue`: `"Ligne 3 de prière"` appears 2 times instead of 1 in the parsed segments.

3. **French NLP Keyword Blind Spots on Hyphenated Terms & Dialogue Punctuation (`src/clip_extractor.py`)**:
   - In `src/clip_extractor.py`, lines 84-95:
     ```python
     def normalize_french_word(word: str) -> str:
         w = word.lower().strip()
         elision_pattern = r"^(?:qu|[ldcsmtnj])['’]"
         w = re.sub(elision_pattern, "", w)
         return "".join(c for c in w if c.isalpha())
     ```
   - In `src/clip_extractor.py`, line 167:
     ```python
     words = seg_text.split()
     for w in words:
         kw_score, kw_matched = find_keyword_match(w)
     ```
   - When extracting words from `seg_text`, `str.split()` does not split on hyphens. The compound term `"Jésus-Christ"` produces `clean_raw = "jésuschrist"`. Since `"jésuschrist"` is not in `VIRAL_KEYWORDS`, `find_keyword_match("Jésus-Christ")` returns `(0.0, None)`. Similarly, `"Dieu-le-Père"` and `"Saint-Esprit"` yield `(0.0, None)`.
   - The regex `elision_pattern = r"^(?:qu|[ldcsmtnj])['’]"` is anchored to the start of the string (`^`). When subtitles contain dialogue dashes (`"-l'onction"`), French guillemets (`"«l'onction»"`), parentheses (`"(l'onction)"`), or quotation marks, `^` does not match the elision. Stripping non-alpha characters then reduces `"-l'onction"` to `"lonction"`, returning `(0.0, None)`.
   - Empirically confirmed in `test_vulnerability_hyphenated_biblical_terms_missed` and `test_vulnerability_leading_punctuation_breaks_elision`.

4. **Successful Hardened Features Verified**:
   - Non-breaking spaces (`\u00a0` and `\u202f`) are handled correctly by Python whitespace splitting (`test_non_breaking_spaces_in_clip_text`).
   - All-caps accents (`ÉTERNEL`, `BÉNÉDICTIONS`, `PRIÈRE`) and elisions (`L’ÉTERNEL`, `D'ONCTIONS`) are properly normalized when not preceded by punctuation.
   - ASS subtitle formatting handles BMP emojis (`⚡`, `✝️`, `⚠️`, `⭐`), ZWJ, and variation selectors (`\ufe0f`) without leaking into ASS script.
   - Complex titles with spaces, colons, brackets, and accents render successfully in FFmpeg as long as single quotes are not present (`test_ffmpeg_rendering_with_spaces_colons_and_accents_succeeds`).

---

## 2. Logic Chain

1. **Premise 1 (Single Quotes in FFmpeg ASS Filter)**:
   - FFmpeg filtergraph syntax parses `'...'` strings literally. A backslash `\` inside a single-quoted string is treated as a literal backslash, not an escape character.
   - Therefore, in `ass='path\'quote.ass'`, the second `'` closes the argument string prematurely, causing the remainder of the path and the output pad `[subbed]` to be parsed as unquoted tokens or invalid filter parameters.
   - Observation 1 demonstrates this directly: passing any path with `'` to FFmpeg fails with exit code 1.
   - Since Karl's domain is French Christian preaching in Côte d'Ivoire, titles and file names naturally contain apostrophes (`l'onction`, `côte d'ivoire`).
   - Hence, `escape_ass_path_for_ffmpeg` and `temp_{output_filename}.ass` represent a critical defect.

2. **Premise 2 (VTT Rolling Deduplication Context)**:
   - Rolling captions maintain an $M$-line sliding window across cues.
   - When cue $i$ is trimmed, it only stores the new delta lines (e.g. line $k$).
   - When cue $i+1$ arrives, its prefix consists of lines from cue $i-1$ and cue $i$, not just the delta in `segments[-1]`.
   - Comparing cue $i+1$ only against `segments[-1]` loses the sliding window history, causing overlap detection to fail and lines to be duplicated.
   - Observation 2 demonstrates this directly on 5-line rolling cues.

3. **Premise 3 (French NLP Tokenization & Punctuation Anchoring)**:
   - `str.split()` separates by whitespace, leaving hyphens intact. Compound biblical terms (`Jésus-Christ`) are stripped to `"jésuschrist"` and fail keyword lookup.
   - Leading punctuation (dialogue dashes in subtitle tracks, quotes, guillemets) blocks `^` in `elision_pattern`, causing `"lonction"` to be formed instead of `"onction"`.
   - Observation 3 directly confirms 0.0 scores for both cases.

---

## 3. Caveats

- Tests were run on local synthetic video fixtures and WebVTT files without live network requests to YouTube.
- Linux filesystem allows colons and single quotes in filenames; Windows NTFS forbids colons in filenames.
- The defect in `escape_ass_path_for_ffmpeg` occurs specifically because the temporary ASS filename is constructed from `output_filename`. If the temporary file path is guaranteed to be clean ASCII without single quotes or colons, FFmpeg renders without issues.

---

## 4. Conclusion

**Verdict: `REQUEST_CHANGES`**

While Worker M2 made significant progress (CPU blur acceleration, Safe Zone MarginR=140, BMP emoji stripping, isolated session downloads), 3 distinct failure modes remain that must be resolved:

1. **[CRITICAL] FFmpeg ASS Path Escaping**:
   - In `src/video_formatter.py`: Generate intermediate `.ass` files using a sanitized, safe filename (e.g. `temp_sub_{uuid.uuid4().hex[:10]}.ass`) rather than embedding raw `output_filename`.
   - In `escape_ass_path_for_ffmpeg(path)`: If path contains single quotes, replace single quotes or sanitize the temp path so FFmpeg filtergraph never receives unescapable single quotes.

2. **[HIGH] Multi-Line Rolling WebVTT Deduplication**:
   - In `src/transcriber.py`: When parsing rolling cues in `_parse_vtt`, do not compare incoming cues solely against the trimmed `segments[-1]["text"]`. Maintain a rolling buffer of the previous un-trimmed cue text (or recent lines) for overlap detection with `deduplicate_rolling_text`.

3. **[MEDIUM] French NLP Compound Words & Leading Punctuation**:
   - In `src/clip_extractor.py`:
     - Strip leading and trailing non-alphanumeric punctuation (e.g. `w.strip("-_«»\"'()[]{}...,;!? ")`) before applying `elision_pattern`.
     - In `find_keyword_match` or word splitting, break on hyphens (`w.split('-')`) so that `"Jésus-Christ"` matches `"jésus"`, `"Dieu-le-Père"` matches `"dieu"`, and `"Saint-Esprit"` can be matched.

---

## 5. Verification Method

To independently verify all findings and reproduced failure modes:

1. **Run the Challenger Adversarial Test Suite**:
   ```bash
   cd /home/antigravity/digrekarlito11-eng/tiktok-autopilot
   .venv/bin/pytest tests/test_adversarial_media_bot.py -v
   ```
   *Expected outcome*: 45 passed in ~3.5 seconds.
   Specifically verifies:
   - `test_vulnerability_single_quote_in_filename_crashes_ffmpeg`: proves single quotes in filename cause FFmpeg `subprocess.CalledProcessError` (exit code 1).
   - `test_vulnerability_multi_line_rolling_window_fails_after_first_cue`: proves 5-line rolling WebVTT duplicates lines.
   - `test_vulnerability_hyphenated_biblical_terms_missed`: proves `"Jésus-Christ"` returns score 0.0.
   - `test_vulnerability_leading_punctuation_breaks_elision`: proves `"-l'onction"` returns score 0.0.

2. **Run Existing Media-Bot Suite**:
   ```bash
   .venv/bin/pytest tests/test_media_bot.py -v
   ```
   *Expected outcome*: 33 passed in ~8 seconds.
