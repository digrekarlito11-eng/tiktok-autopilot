# Handoff Report: Media-Bot Survey & Architectural Analysis

## 1. Observation

### 1.1 Codebase Structure and Components Under Survey
- **Repository path**: `/home/antigravity/digrekarlito11-eng/tiktok-autopilot`
- **Core Media-Bot files**:
  - `src/downloader.py` (98 lines) — `VideoDownloader` using `yt-dlp`
  - `src/transcriber.py` (116 lines) — `VideoTranscriber` (native VTT parsing + `faster-whisper` fallback)
  - `src/clip_extractor.py` (135 lines) — `ClipExtractor` (viral keyword scoring & duration windowing)
  - `src/video_formatter.py` (184 lines) — `VideoFormatter` (ASS subtitle generation & FFmpeg 9:16 filtergraph)
  - `src/themes.py` (50 lines) — Color palettes & font settings for `gospel`, `gold`, `neon`, `minimal`
  - `src/pipeline.py` (183 lines) — Orchestrator tying Media-Bot, Growth-Bot, and DevOps-Bot
  - `main.py` (122 lines) — CLI entry point & synthetic demo generator
  - `.github/workflows/generate_tiktok.yml` (90 lines) — CI/CD execution definition

### 1.2 Video Downloading (`src/downloader.py`)
- **CLI Subprocess Invocations**:
  - Line 27: executes `["yt-dlp", "--dump-json", "--no-playlist", url]`
  - Line 53: executes `["yt-dlp", "--format", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best", "--write-auto-subs", "--write-subs", "--sub-langs", "fr.*,en.*", "--sub-format", "vtt/best", "--no-playlist", "--output", output_template, url]`
- **Observation on Execution Environment**:
  - Executing `which yt-dlp` on the host returned exit code 1 (`Not in PATH`).
  - Executing `.venv/bin/yt-dlp --version` returned `2026.10.26`.
  - In `src/downloader.py`, `subprocess.run(["yt-dlp", ...])` fails with `FileNotFoundError` unless `.venv/bin` is explicitly in `$PATH` or invoked via `sys.executable -m yt_dlp`.
- **Double Network Call**:
  - Separate `info_cmd` and `dl_cmd` calls double HTTP handshake latency and increase risk of YouTube bot-detection/HTTP 429 rate limiting.
- **File Matching Edge Case** (lines 70–86):
  ```python
  if not video_file:
      for fname in os.listdir(self.download_dir):
          if fname.endswith(".mp4"):
              video_file = os.path.join(self.download_dir, fname)
              break
  ```
  If `video_id` matching fails, the code silently selects an arbitrary existing `.mp4` file from `downloads/`, causing incorrect video processing in batch or repeated runs.

### 1.3 Transcription and VTT Parsing (`src/transcriber.py`)
- **Timestamp Parsing** (lines 6–15):
  `parse_vtt_timestamp` supports `H:M:S.m` and `M:S.m` formats.
- **YouTube Auto-Generated Rolling VTT Defect**:
  - Tested with simulated YouTube auto-generated VTT (`test_yt.vtt`):
    ```
    00:00:01.000 --> 00:00:03.500: Dieu va faire un miracle
    00:00:03.500 --> 00:00:06.000: Dieu va faire un miracle dans ta vie reçois
    00:00:06.000 --> 00:00:09.000: dans ta vie reçois cette bénédiction aujourd'hui
    ```
  - Result: Text is repeated across consecutive cues: `"Dieu va faire un miracle Dieu va faire un miracle dans ta vie reçois dans ta vie reçois cette bénédiction aujourd'hui"`. `clean_subtitle_text` strips HTML tags but lacks progressive cue deduplication.
- **Whisper Fallback (`src/transcriber.py:89–116`)**:
  - Converts entire source video to uncompressed 16kHz WAV (`pcm_s16le`) via FFmpeg before calling `faster_whisper`.
  - Default model is `model_size="tiny"`, `device="cpu"`, `compute_type="int8"`.
  - `model.transcribe(audio_path, language="fr")` does not set `initial_prompt`, `vad_filter`, or `word_timestamps=True`.
  - Subtitles rely on linear interpolation chunking rather than real word-level timestamps.

### 1.4 Highlight Detection and Scoring (`src/clip_extractor.py`)
- **Keyword Matching Limitation**:
  - `clean_w = "".join(c for c in w if c.isalpha())`
  - Tested against real spiritual phrasing:
    - `"Dieu va faire des miracles dans ta vie"`: matched only `["dieu"]` (3.5 pts); `"miracles"` (ending with `s`) failed to match `"miracle"` (4.0 pts missed).
    - `"Reçois toutes ces bénédictions prophétiques"`: matched `[]` (0 pts); both plural words missed.
    - `"L'Éternel est mon berger"`: matched `[]` (0 pts); `"l'éternel"` becomes `"léternel"`.
    - `"C'est l'onction de Dieu"`: matched only `["dieu"]` (3.5 pts); `"l'onction"` becomes `"lonction"` and missed `"onction"`.
- **Duration Constraint**:
  - `min_duration=25.0`, `max_duration=58.0`.
  - Nested loop terminates when `duration > max_duration`, resulting in fast $O(N)$ practical complexity (~15 iterations per segment).
- **Deduplication Logic**:
  - Comment says `# Vérifier qu'il ne chevauche pas un clip déjà sélectionné à plus de 50%`, but code enforces strict zero-overlap: `not (cand["end"] < s["start"] or cand["start"] > s["end"])`.

### 1.5 FFmpeg 9:16 Vertical Render, Blurred Background, Themes, Progress Bar (`src/video_formatter.py`, `src/themes.py`)
- **Render Execution & Output Inspection**:
  - Executed `run_synthetic_demo` generating `output/tiktok_Masterclass Karl Stu_clip_1_0s.mp4`.
  - Probe: duration `33.50s`, resolution `1080x1920` (DAR 9:16), H.264 High profile, 30 fps, AAC audio 132 kb/s.
  - Frame inspection (`frame_2s.png`, `frame_15s.png`, `frame_30s.png`):
    - Top banner: Watermark `@parole.de.foi` top-left ($y=210$), Hook title centered ($y=240$) in celestial gold with black border.
    - Central video: 16:9 foreground perfectly sharp and centered.
    - Background: Top and bottom vertical extensions filled with blurred background.
    - Progress bar: Golden bar at $y=1906$ ($h=14\text{px}$) animated from 0 to 1080px across the clip duration.
    - Subtitles: Positioned at MarginV=480 (bottom center), white with black border, with the first word of each 5-word chunk highlighted in gold.
- **Theme Definitions**:
  - Gospel theme: `hook_color="&H0000D7FF&"` (ASS BGR format for `#FFD700` Gold), `sub_primary="&H00FFFFFF&"` (White), `progress_color="0xFFD700"` (FFmpeg hex for Gold). Perfectly consistent.
- **Performance Bottleneck in Filtergraph**:
  - `[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg]`
  - Applying `boxblur=25:5` on 2,073,600 pixels per frame runs at only ~0.58x–0.65x realtime on CPU.
- **ASS File Path Escaping**:
  - `f"[merged]ass={ass_path}[subbed]"`
  - `ass_path` is not wrapped in quotes or escaped. Spaces in `video_title` (e.g. `Masterclass Karl Stu`) produce spaces in filtergraph arguments, which risks breaking in strict FFmpeg filter parsers or on paths with colons.
- **Safe Zone Collision Risk**:
  - `MarginR=60` for subtitles. TikTok's right-side interaction bar (avatar, like, comment, share) spans 120–140px from the right edge. Subtitles spanning the full width can be obstructed by TikTok UI buttons.
- **Emoji Handling**:
  - `clean_text_for_ass` regex `[\U00010000-\U0010ffff]` strips SMP emojis (`🕊️`, `🙏`), but leaves behind dangling Variation Selector-16 (`\uFE0F`) and BMP symbols (`✝`, `⚡`, `⚔`).

### 1.6 External Pipeline Blocker Observed During Survey
- `main.py --demo` failed after successful video rendering with:
  `KeyError: 'karl_studio_link'` at `src/growth_optimizer.py:129`.
  `package` in `generate_growth_package()` lacks the `'karl_studio_link'` key expected by `export_summary_sheet()`.

### 1.7 Test Suite Status
- Repository contains zero test files: `find_by_name` for `*test*` returned 0 results. No pytest configuration, fixtures, or unit tests exist.

---

## 2. Logic Chain

1. **Environment & Invocation Reliability**:
   - Because `downloader.py` executes `"yt-dlp"` as a naked command and `yt-dlp` is only installed inside `.venv`, running `python main.py` outside an activated venv causes immediate process death (`FileNotFoundError`).
   - Using `[sys.executable, "-m", "yt_dlp", ...]` or the direct Python API `import yt_dlp; yt_dlp.YoutubeDL(...)` guarantees execution across any Python environment where dependencies are installed.
2. **Quality of Transcription & Viral Accuracy**:
   - Because YouTube auto-generated VTT uses a rolling 2–3 line window, straightforward cue concatenation creates repetitive stutter in the parsed segments.
   - Because `ClipExtractor` uses exact word comparison against `VIRAL_KEYWORDS`, common French morphological variations (plurals like `miracles`, elisions like `l'onction`, `l'éternel`, and verb forms) are ignored, systematically undervaluing prime preaching clips.
3. **FFmpeg Encoding Speed**:
   - `boxblur=25:5` on a full 1080x1920 frame requires 5 passes over 2.07 million pixels for every video frame.
   - Downscaling the background stream before blurring (e.g., to 108x192) and then upscaling to 1080x1920 preserves visual softness while reducing blur pixel count by 99%, boosting render speed from 0.6x to 3x–5x.
4. **Visual Layout & Safety**:
   - Visual inspection of rendered frames validates that the gospel gold/white theme, blurred canvas, hook header, and golden progress bar render correctly and adhere to 9:16 geometry.
   - Increasing subtitle `MarginR` from 60 to 140 protects text from colliding with TikTok's right-hand action column.
5. **System Validation & Stability**:
   - The failure of `main.py --demo` due to `KeyError: 'karl_studio_link'` proves that end-to-end regression testing is required before deploying autonomous pipelines.

---

## 3. Caveats

1. **Audio Energy Scoring**:
   Highlight extraction is currently 100% lexical (text-based). Audio pitch/volume surges (e.g. pastor shouting, congregation shouting "Amen") are not evaluated.
2. **GPU Acceleration**:
   Investigation focused on CPU rendering (GitHub Actions `ubuntu-latest` / standard VPS). If NVENC or VAAPI hardware acceleration is available in production, FFmpeg flags can be optimized further.
3. **YouTube Throttling / Bot Detection**:
   yt-dlp operations against YouTube can be subject to IP rate-limits or bot checks unless `--cookies` or OAuth tokens are provided.

---

## 4. Conclusion

The Media-Bot core rendering architecture is structurally solid and visually compliant with TikTok 9:16 vertical standards, featuring an aesthetic celestial gold/white gospel theme, centered foreground video with blurred backdrop, and a golden bottom progress bar.

However, 6 concrete improvements are required for enterprise robustness:
1. **Downloader**: Switch to `sys.executable -m yt_dlp` or Python API `yt_dlp.YoutubeDL`, merge info extraction with download in a single request, and enforce isolated download folders per job to eliminate wrong-file fallback risks.
2. **VTT Deduplication**: Add rolling-window cue deduplication in `VideoTranscriber._parse_vtt` to eliminate repeated text from YouTube auto-generated captions.
3. **Highlight Extractor**: Implement French word normalization (strip `l'`, `d'`, and terminal `s`/`x`) and expand `VIRAL_KEYWORDS` to cover plural/elided forms (`miracles`, `prières`, `bénédictions`, `l'éternel`, `l'onction`).
4. **FFmpeg Filtergraph Optimization**: Downscale background before applying `boxblur` (`scale=108:192,boxblur=5:2,scale=1080:1920`) to achieve 5x faster CPU encoding, and safely quote/escape `ass_path`.
5. **Safe Zone Margin**: Increase `MarginR` to 140 in ASS styles to prevent collision with TikTok right-side UI buttons.
6. **Test Suite**: Establish a comprehensive unit and integration test suite (`tests/test_media_bot.py`) covering downloading, VTT parsing, highlight extraction, theme resolution, and video formatting.

---

## 5. Verification Method

### 5.1 End-to-End Synthetic Demo Run
```bash
cd /home/antigravity/digrekarlito11-eng/tiktok-autopilot
.venv/bin/python main.py --demo --theme gospel --watermark "@parole.de.foi"
```
*Expected Result*: Must generate `output/tiktok_Masterclass Karl Stu_clip_1_0s.mp4` and exit 0 without KeyError.

### 5.2 FFprobe Geometry and Stream Validation
```bash
ffprobe -v error -show_entries stream=width,height,codec_name,r_frame_rate -of default=noprint_wrappers=1 "output/tiktok_Masterclass Karl Stu_clip_1_0s.mp4"
```
*Expected Output*:
```
codec_name=h264
width=1080
height=1920
r_frame_rate=30/1
```

### 5.3 Media-Bot Isolated Verification Script
```bash
.venv/bin/python .agents/teamwork/explorer_survey_2/verify_media_bot.py
```
*Invalidation Conditions*:
- Fails if VTT timestamps fail to convert to seconds.
- Fails if theme colors deviate from gospel gold (`#FFD700`).
- Fails if FFmpeg is unable to decode the generated 9:16 vertical video.
