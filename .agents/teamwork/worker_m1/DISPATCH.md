# Task Assignment: Worker M1 (DevOps-Bot & Pipeline Core)

## Mission
Implement the required fixes and enhancements for Milestone 1 (DevOps-Bot & Pipeline Core) in `/home/antigravity/digrekarlito11-eng/tiktok-autopilot`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks to Implement
1. **Fix P0 KeyError (`karl_studio_link`) in `src/growth_optimizer.py:129`**:
   - In `export_summary_sheet()`, replace `package['karl_studio_link']` with:
     `package.get('karl_studio_link', 'https://digrekarlito11-eng.github.io/karl-studio/')`
   - Include `location_focus: {package.get('location_focus', "Côte d'Ivoire (GMT / Abidjan) & Diaspora")}` in the exported summary.
2. **Implement Phase 2 Video Binary Upload in `src/tiktok_publisher.py`**:
   - After `POST /v2/post/publish/video/init/` succeeds and returns `upload_url` and `publish_id`, read the video bytes from `video_path`.
   - Send HTTP `PUT` request to `upload_url` with headers `Content-Type: video/mp4` and `Content-Range: bytes 0-{video_size - 1}/{video_size}`.
   - Gracefully handle offline / draft mode when `TIKTOK_ACCESS_TOKEN` is not set: ensure `output/<clip_name>_tiktok_payload.json` is saved cleanly and documented.
3. **Harden `.github/workflows/generate_tiktok.yml`**:
   - Inject `TIKTOK_WEBHOOK_URL: ${{ secrets.TIKTOK_WEBHOOK_URL }}` in the job environment.
   - Pass user inputs as environment variables (e.g. `VIDEO_URL`, `CLIPS_COUNT`, `THEME`, `WATERMARK`, etc.) into `python main.py` rather than inline shell interpolation, preventing bash syntax errors or injection on quotes.
4. **Create CI Workflow (`.github/workflows/ci.yml`)**:
   - Set up Python, install dependencies and ffmpeg, run pytest.
5. **Add Unit Tests in `tests/test_devops_bot.py`**:
   - Unit tests covering `TikTokPublisher` (payload structure, offline draft JSON generation, mock init & mock PUT upload), `Notifier` (webhook generation with mock HTTP), `main.py` CLI arguments.
6. **Verification**:
   - Run tests: `.venv/bin/pytest tests/test_devops_bot.py -v`
   - Run synthetic demo: `.venv/bin/python main.py --demo`
   - Confirm code exit 0 with all artifacts generated under `output/`.

## File Ownership (Strict Write Exclusivity)
- `src/growth_optimizer.py`
- `src/tiktok_publisher.py`
- `.github/workflows/generate_tiktok.yml`
- `.github/workflows/ci.yml`
- `tests/test_devops_bot.py`

## Output
Write a complete handoff report to `/home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/worker_m1/handoff.md` with:
- Detailed changes made
- Build and test commands executed with stdout/stderr
- Verification results
Report back via send_message when complete.


## 2026-11-12T18:54:42Z
You are Worker M1 (DevOps-Bot & Pipeline Core).
Working directory: /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/worker_m1
Read /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/ORIGINAL_REQUEST.md, /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/PROJECT.md, and /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/worker_m1/DISPATCH.md.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write targets:
- src/growth_optimizer.py (Fix P0 KeyError: 'karl_studio_link')
- src/tiktok_publisher.py (Implement Phase 2 binary HTTP PUT video upload)
- .github/workflows/generate_tiktok.yml (Inject TIKTOK_WEBHOOK_URL, safe env variables)
- .github/workflows/ci.yml (Create CI workflow)
- tests/test_devops_bot.py (Create unit tests)

Execute tests (.venv/bin/pytest tests/test_devops_bot.py -v) and run synthetic demo (.venv/bin/python main.py --demo).
Write your complete handoff report to /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/worker_m1/handoff.md and report back via send_message when done.
