# Task Assignment: Worker M2 (Media-Bot Pipeline Hardening)

## Mission
Harden and optimize the Media-Bot video processing pipeline in `/home/antigravity/digrekarlito11-eng/tiktok-autopilot`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks to Implement
1. **Downloader Resiliency (`src/downloader.py`)**:
   - In `_download_video()` and `get_video_info()`, execute `[sys.executable, "-m", "yt_dlp", ...]` instead of naked `"yt-dlp"` so that the active virtualenv yt-dlp is always found even if not in system `$PATH`.
   - Prevent arbitrary fallback that picks an unrelated `.mp4` file in `self.download_dir`. Use unique session subdirectories or strict video_id matching; raise clear error if download fails.
2. **VTT Caption Deduplication (`src/transcriber.py`)**:
   - In `_parse_vtt()`, implement rolling-window deduplication so that YouTube auto-generated captions do not duplicate rolling text across adjacent cues.
3. **French NLP in Highlight Extractor (`src/clip_extractor.py`)**:
   - Normalize French words by stripping leading `l'`, `d'`, `c'`, `qu'` and terminal `s`, `x` for singular/plural matching.
   - Expand `VIRAL_KEYWORDS` with spiritual terms: `miracle`, `miracles`, `priere`, `prieres`, `benediction`, `benedictions`, `eternel`, `onction`, `combat`, `combats`, `delivrance`, `foi`, `grace`, etc.
4. **FFmpeg Render Optimization & Safe Zone (`src/video_formatter.py`)**:
   - Optimize background blur: scale down background prior to blur and scale back up (`scale=108:192,boxblur=5:2,scale=1080:1920`) for 5x CPU acceleration while preserving smooth blur aesthetics.
   - Increase subtitle right margin to `MarginR=140` in ASS style headers to prevent collision with TikTok UI buttons.
   - Safely escape `ass_path` in FFmpeg filtergraph: wrap in escaped quotes or escape colons/slashes so spaces in filenames never break the filter.
   - Enhance `clean_text_for_ass()` to clean BMP emojis and selector `\ufe0f`.
5. **Tests & Verification**:
   - Update and expand `tests/test_media_bot.py` covering all new behavior.
   - Run tests: `.venv/bin/pytest tests/test_media_bot.py -v`
   - Run full suite: `.venv/bin/pytest tests/ -v`
   - Run synthetic demo: `.venv/bin/python main.py --demo`
   - Check that output video `output/tiktok_Masterclass Karl Stu_clip_1_0s.mp4` is valid 1080x1920 9:16 video.

## File Ownership (Strict Write Exclusivity)
- `src/downloader.py`
- `src/transcriber.py`
- `src/clip_extractor.py`
- `src/video_formatter.py`
- `tests/test_media_bot.py`

## Output
Write a complete handoff report to `/home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/worker_m2/handoff.md` with:
- Detailed changes made
- Build and test commands executed with stdout/stderr
- Verification results
Report back via send_message when complete.


## 2026-11-12T19:24:04Z
You are Worker M2 (Media-Bot Pipeline Hardening).
Working directory: /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/worker_m2
Read /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/ORIGINAL_REQUEST.md, /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/PROJECT.md, and /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/worker_m2/DISPATCH.md.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write targets:
- src/downloader.py (sys.executable -m yt_dlp, remove dangerous mp4 fallback, isolated downloads)
- src/transcriber.py (rolling-window VTT cue deduplication)
- src/clip_extractor.py (French NLP elisions/plurals & expanded VIRAL_KEYWORDS)
- src/video_formatter.py (downscaled blur acceleration, MarginR=140, ass_path escaping, emoji cleaning)
- tests/test_media_bot.py (expanded tests)

Execute tests (.venv/bin/pytest tests/test_media_bot.py -v, .venv/bin/pytest tests/ -v) and run synthetic demo (.venv/bin/python main.py --demo).
Write your complete handoff report to /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/worker_m2/handoff.md and report back via send_message when done.
