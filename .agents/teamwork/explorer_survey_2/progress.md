# Progress Log

Last visited: 2026-11-12T18:52:00Z

- Explored full Media-Bot codebase (`downloader.py`, `transcriber.py`, `clip_extractor.py`, `video_formatter.py`, `themes.py`, `pipeline.py`).
- Conducted end-to-end synthetic run (`main.py --demo`), inspected generated MP4 video with ffprobe and visual frames with ffmpeg.
- Executed empirical verification script (`verify_media_bot.py`) testing VTT parsing, keyword scoring with plurals/apostrophes, emoji cleaning in ASS subtitles, and themes.
- Discovered multiple critical findings:
  1. `growth_optimizer.py` missing `'karl_studio_link'` causing `KeyError` during sheet generation in `--demo`.
  2. YouTube auto-generated VTT rolling cues causing duplicate/repeated text in subtitle segments.
  3. Plural keywords and French apostrophe words (e.g. `miracles`, `bénédictions`, `l'onction`, `l'éternel`) scoring 0 in viral highlight detection.
  4. Video downloader uses CLI subprocess `yt-dlp` rather than `sys.executable -m yt_dlp` or Python API `yt_dlp.YoutubeDL`, which fails if not in system PATH.
  5. Boxblur 25:5 CPU bottleneck on full 1080x1920 (0.6x realtime) can be sped up 5x-10x by downscaling before blurring.
  6. Subtitle chunking only highlights the first word of each 5-word chunk rather than synchronized word-by-word karaoke.
  7. Zero test suite coverage (no `tests/` directory or `pytest` setup).
- Preparing comprehensive 5-component handoff report.
