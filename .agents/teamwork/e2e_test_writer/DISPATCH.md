# Task Assignment: E2E Test Writer (Dual Track)

## Mission
Design and implement a comprehensive E2E test suite for `tiktok-autopilot` under `/home/antigravity/digrekarlito11-eng/tiktok-autopilot/tests/` using `pytest`.
The test suite must be opaque-box, requirement-driven, derived from `ORIGINAL_REQUEST.md` and `PROJECT.md § Feature Inventory`.

## Methodology (4 Tiers)
1. **Tier 1 - Feature Coverage**:
   - Verify every core feature in isolation (DevOps-Bot CLI & draft payload, Media-Bot downloader/formatter/themes, Growth-Bot prophetic hooks/captions/hashtags/GMT slots).
2. **Tier 2 - Boundary & Corner Cases**:
   - Empty strings, very short (<10s) and long (>60s) inputs, missing environment variables, special characters in title/watermark, rolling VTT caption deduplication, invalid video URLs.
3. **Tier 3 - Cross-Feature Interactions**:
   - Integration of Media-Bot + Growth-Bot + TikTokPublisher payload pipeline, theme color matching between ASS and progress bar, watermark positioning in Safe Zone.
4. **Tier 4 - Real-World Application Scenarios**:
   - End-to-end synthetic preaching workflow test simulating Karl's autonomous experience from Abidjan.

## File Ownership
- `tests/conftest.py`
- `tests/test_e2e_pipeline.py`
- `tests/test_growth_bot.py`
- `TEST_INFRA.md`
- `TEST_READY.md` (to be created at `/home/antigravity/digrekarlito11-eng/tiktok-autopilot/TEST_READY.md` when the test suite is ready)

## Handoff Requirements
Run the test suite via `.venv/bin/pytest tests/ -v`, record all results, and write a complete handoff report to:
`/home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/e2e_test_writer/handoff.md`.


## 2026-11-12T18:54:42Z
[Message] timestamp=2026-11-12T18:54:42Z sender=0b15047f2814c727611000b3f1df5d16 priority=MESSAGE_PRIORITY_HIGH content=You are E2E Test Writer for the tiktok-autopilot project.
Working directory: /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/e2e_test_writer
Read /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/ORIGINAL_REQUEST.md, /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/PROJECT.md, and /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/e2e_test_writer/DISPATCH.md.
Design and implement a comprehensive test suite in /home/antigravity/digrekarlito11-eng/tiktok-autopilot/tests/ (e.g. tests/conftest.py, tests/test_e2e_pipeline.py, tests/test_growth_bot.py).
Do NOT modify existing implementation code in src/ or main.py.
Follow the 4-tier methodology (Tier 1 Feature coverage, Tier 2 Boundary/corners, Tier 3 Cross-feature, Tier 4 Real-world preaching workflow).
Create /home/antigravity/digrekarlito11-eng/tiktok-autopilot/TEST_INFRA.md and publish /home/antigravity/digrekarlito11-eng/tiktok-autopilot/TEST_READY.md when tests are ready.
Run the tests using .venv/bin/pytest tests/ -v.
Write your complete handoff report to /home/antigravity/digrekarlito11-eng/tiktok-autopilot/.agents/teamwork/e2e_test_writer/handoff.md and report back via send_message when done.
