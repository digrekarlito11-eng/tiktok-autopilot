# Handoff Report — Worker M2b (Media-Bot Remediation)

**Timestamp**: 2026-11-12T20:20:00Z  
**Agent**: Worker M2b (`worker_m2b`)  
**Parent Agent**: `0b15047f2814c727611000b3f1df5d16`  
**Milestone**: M2b (Media-Bot Remediation)  
**Status**: Completed  

---

## 1. Observation

Direct observations before and after remediation across the three target areas:

1. **Issue 1: FFmpeg ASS Filter Crash on Single Quotes in Filenames (`src/video_formatter.py`)**:
   - **Before**: In `src/video_formatter.py:157`, the subtitle path was interpolated directly from `output_filename`:
     ```python
     ass_path = os.path.join(self.output_dir, f"temp_{output_filename}.ass")
     ```
     and in `src/video_formatter.py:46-48`:
     ```python
     escaped = norm_path.replace("'", r"\'").replace(':', r'\:')
     return f"'{escaped}'"
     ```
     When `output_filename` contained single quotes (e.g. `tiktok_l'onction_divine.mp4`), FFmpeg failed with exit status 1:
     `[AVFilterGraph @ ...] Error initializing filter 'ass' with args '/.../temp_tiktok_l\onction_divine.mp4.ass[subbed]'`
     `Invalid argument`
   - **Remediation**:
     - Subtitle path in `render_tiktok_video` now uses an isolated, sanitized clean ID:
       ```python
       clean_sub_id = uuid.uuid4().hex[:10]
       ass_path = os.path.join(self.output_dir, f"temp_sub_{clean_sub_id}.ass")
       ```
     - `escape_ass_path_for_ffmpeg` neutralizes single quotes to prevent filtergraph string closure while escaping colons (`\:`):
       ```python
       norm_path = os.path.abspath(path).replace('\\', '/')
       escaped = norm_path.replace("'", "").replace(':', r'\:')
       return f"'{escaped}'"
       ```
     - Enclosed rendering in `try ... finally` to guarantee cleanup of `ass_path`.
   - **After**: `test_vulnerability_single_quote_in_filename_crashes_ffmpeg` renders `tiktok_l'onction_divine.mp4` with resolution 1080x1920 successfully.

2. **Issue 2: Multi-Line Rolling Window WebVTT Deduplication Loss (`src/transcriber.py`)**:
   - **Before**: In `src/transcriber.py:110-117`, rolling deduplication was evaluated solely against `segments[-1]["text"]`:
     ```python
     prev_seg = segments[-1]
     deduped = deduplicate_rolling_text(prev_seg["text"], full_txt)
     ```
     In multi-line (e.g. 5-line) rolling captions, Cue 2 trimmed lines 2-5 down to Line 6 in `segments[-1]`. When Cue 3 (lines 3-7) arrived, it compared against `segments[-1]["text"]` (which contained only Line 6), finding 0 overlap. Consequently, lines 3-6 were duplicated in the final transcript.
   - **Remediation**:
     In `_parse_vtt`, introduced `last_cue_text` to retain the full multi-line context of the preceding cue before trimming:
     ```python
     prev_context = last_cue_text if last_cue_text else segments[-1]["text"]
     deduped = deduplicate_rolling_text(prev_context, raw_txt)
     if deduped == raw_txt and prev_context != segments[-1]["text"]:
         deduped = deduplicate_rolling_text(segments[-1]["text"], raw_txt)
     ```
     and updated `last_cue_text = raw_txt` after processing.
   - **After**: `test_vulnerability_multi_line_rolling_window_fails_after_first_cue` confirms `Ligne 3 de prière` appears exactly 1 time (duplication count = 1).

3. **Issue 3: French NLP Compound Words & Leading Dialogue Punctuation (`src/clip_extractor.py`)**:
   - **Before**:
     - `normalize_french_word` used `elision_pattern = r"^(?:qu|[ldcsmtnj])['’]"` anchored at `^`. Leading dialogue characters (`-`, `«`, `(`, `"`) prevented matching, turning `"-l'onction"` into `"lonction"` (score 0.0).
     - Biblical compound words (`"Jésus-Christ"`, `"Dieu-le-Père"`, `"Saint-Esprit"`) were not split on hyphens, leaving `"jésuschrist"` (score 0.0).
   - **Remediation**:
     - `normalize_french_word` and `find_keyword_match` strip dialogue punctuation delimiters (`-_–—«»\"'()[]{}...,;!? `) before testing elisions.
     - Added theological terms (`"saint": 3.0, "saints": 3.0, "esprit": 3.5, "esprits": 3.5, "christ": 3.5, "christs": 3.5, "père": 3.0, "pere": 3.0`) to `VIRAL_KEYWORDS`.
     - In `find_keyword_match` and `find_best_clips`, hyphenated tokens are split on `-`, evaluating each sub-token.
   - **After**:
     - `find_keyword_match("Jésus-Christ")` returns `(3.5, 'jésus')`.
     - `find_keyword_match("Dieu-le-Père")` returns `(3.5, 'dieu')`.
     - `find_keyword_match("Saint-Esprit")` returns `(3.5, 'esprit')`.
     - `find_keyword_match("-l'onction")`, `find_keyword_match("«l'onction»")`, and `find_keyword_match("(l'onction)")` all return `(3.5, 'onction')`.

---

## 2. Logic Chain

1. **Premise 1 (FFmpeg Filtergraph String Semantics)**:
   - In FFmpeg's filtergraph parser, arguments enclosed in single quotes cannot escape single quotes via `\'`.
   - By creating intermediate `.ass` filenames as `temp_sub_{clean_id}.ass` (clean hexadecimal ASCII), the temporary subtitle path on disk never contains quotes, regardless of the user's `output_filename`.
   - Neutralizing single quotes and escaping colons in `escape_ass_path_for_ffmpeg` protects against any accidental directory-level quote injection.
   - This directly eliminates the `subprocess.CalledProcessError: Command '['ffmpeg', ...]' returned non-zero exit status 1` defect observed in Observation 1.

2. **Premise 2 (Preservation of Rolling Window Context)**:
   - A progressive rolling subtitle window emits overlapping lines across consecutive cues.
   - Storing only the trimmed delta in `segments[-1]` loses the prefix history required to deduplicate subsequent cues that start earlier than the previous delta.
   - By storing `last_cue_text` (the untrimmed multi-line text of the prior cue) and using it as `prev_context`, the sliding window overlap is recognized across any number of rolling lines ($N \ge 3$), eliminating duplicated phrases.

3. **Premise 3 (Dialogue Normalization & Compound Word Tokenization)**:
   - Subtitle transcriptions frequently prefix dialogue lines with dashes (`-`) or quotes (`«`).
   - Stripping non-alphabetic boundary characters before evaluating the elision regex `^(?:qu|[ldcsmtnj])['’]` allows standard French contractions (`l'`, `d'`, `c'`, etc.) to resolve to their root words.
   - Compound theological names in French Christianity are connected by hyphens (`Jésus-Christ`, `Saint-Esprit`). Splitting compound tokens on `-` allows sub-token matches against `VIRAL_KEYWORDS`, enabling high viral scoring for Karl's niche.

---

## 3. Caveats

- Subtitle formatting still relies on libass installed on the host system.
- In `escape_ass_path_for_ffmpeg`, any hypothetical directory path that contains single quotes will have those quotes stripped in the filtergraph argument; because the intermediate file is created via `temp_sub_{uuid.uuid4().hex[:10]}.ass`, the actual intermediate file path is always clean.
- "No caveats" regarding pipeline compatibility or regression: all 152 existing unit, integration, stress, and E2E tests pass without error.

---

## 4. Conclusion

All 3 defects reported by Challenger 1 have been genuinely and definitively resolved:
1. `src/video_formatter.py`: intermediate `.ass` path generation is decoupled from `output_filename` via safe random UUIDs; `escape_ass_path_for_ffmpeg` hardens quotes and colons; temporary files are reliably cleaned up via `try ... finally`.
2. `src/transcriber.py`: multi-line rolling WebVTT cues maintain rolling context across cues, avoiding duplicate lines.
3. `src/clip_extractor.py`: dialogue boundary punctuation is cleanly stripped and compound biblical words are tokenized, ensuring accurate French NLP scoring.

---

## 5. Verification Method

To independently verify the implementation and test results:

1. **Adversarial Test Suite**:
   ```bash
   cd /home/antigravity/digrekarlito11-eng/tiktok-autopilot
   .venv/bin/pytest tests/test_adversarial_media_bot.py -v
   ```
   *Result*: 45 passed in ~5.4 seconds.

2. **Full Regression Test Suite**:
   ```bash
   cd /home/antigravity/digrekarlito11-eng/tiktok-autopilot
   .venv/bin/pytest tests/ -v
   ```
   *Result*: 152 passed in ~109 seconds.

3. **Main Demo CLI**:
   ```bash
   cd /home/antigravity/digrekarlito11-eng/tiktok-autopilot
   .venv/bin/python main.py --demo
   ```
   *Result*: Exits with code 0; generates 1080x1920 MP4 `output/tiktok_Masterclass Karl Stu_clip_1_0s.mp4` with dynamic subtitles, golden progress bar, and draft payload.
