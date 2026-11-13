# Task Assignment: Worker M2b (Media-Bot Remediation)

## Mission
Remediate the 3 specific issues identified by Challenger 1 in Milestone 2:
1. **FFmpeg ASS Filter Crash on Single Quotes**:
   - In `src/video_formatter.py`: create intermediate `.ass` file paths using a sanitized clean name, e.g. `temp_sub_{uuid.uuid4().hex[:10]}.ass`, avoiding raw `output_filename` interpolation.
   - Harden `escape_ass_path_for_ffmpeg` so that single quotes or colons never cause FFmpeg filtergraph syntax errors.
2. **Multi-Line Rolling Window WebVTT Deduplication**:
   - In `src/transcriber.py`: when parsing rolling cues in `_parse_vtt`, preserve rolling window context across cues (do not compare solely against the trimmed `segments[-1]["text"]`).
3. **French NLP Compound Words & Leading Punctuation**:
   - In `src/clip_extractor.py`: strip leading/trailing dialogue punctuation (`-_«»\"'()[]{}`) before applying `elision_pattern`. Split on hyphens (`-`) so `"Jésus-Christ"` matches `"jésus"` and `"Dieu-le-Père"` matches `"dieu"`.

## Reference Inputs
- Challenger 1 handoff: `/home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/challenger_m2_1/handoff.md`
- Adversarial test file: `tests/test_adversarial_media_bot.py`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Verification
- Run: `.venv/bin/pytest tests/test_adversarial_media_bot.py -v`
- Run: `.venv/bin/pytest tests/ -v`
- Run: `.venv/bin/python main.py --demo`
Write handoff to `/home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/worker_m2b/handoff.md` and report back via send_message.
