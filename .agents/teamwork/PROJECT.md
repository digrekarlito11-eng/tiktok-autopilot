# Project: tiktok-autopilot

## Architecture
Le projet `tiktok-autopilot` est une usine de production vidéo 100% autonome dédiée aux prédications chrétiennes pour Karl (Abidjan, Côte d'Ivoire / GMT), publiant exclusivement sur TikTok.
L'architecture est structurée en 3 bots modulaires :
1. **DevOps-Bot** : Orchestration GitHub Actions (`.github/workflows/generate_tiktok.yml`), point d'entrée CLI `main.py`, exécution du pipeline complet `src/pipeline.py`, publication TikTok API v2 en mode brouillon privé (`src/tiktok_publisher.py`), notifications webhook mobile (`src/notifier.py`).
2. **Media-Bot** : Téléchargement vidéo/sous-titres via `yt-dlp` (`src/downloader.py`), transcription & VTT parsing (`src/transcriber.py`), scoring et extraction de moments forts viraux (`src/clip_extractor.py`), composition vidéo FFmpeg 9:16 vertical 1080x1920 avec fond flou, sous-titres dynamiques ASS et barre dorée (`src/video_formatter.py`, `src/themes.py`).
3. **Growth-Bot** : Accroches prophétiques supérieures ("ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️", etc.), structure de description avec CTA d'engagement ("Écris AMEN en commentaire pour sceller cette bénédiction 👇"), 10 hashtags ultra-ciblés chrétiens & Côte d'Ivoire, créneaux de publication optimisés Abidjan GMT, fiches récapitulatives (`src/growth_optimizer.py`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | P0 KeyError Fix | Corriger `package['karl_studio_link']` dans `src/growth_optimizer.py:129` qui fait crasher le pipeline | M1 | Survey |
| 2 | TikTokPublisher API v2 Draft | Implémenter l'étape 2 (HTTP PUT binaire des octets vidéo vers `upload_url`) pour la publication TikTok | M1 | Survey |
| 3 | GitHub Actions Hardening | Injecter `TIKTOK_WEBHOOK_URL`, sécuriser les arguments via variables d'environnement contre l'injection bash, ajouter CI workflow | M1 | Survey |
| 4 | Downloader Resiliency | Invoquer `yt-dlp` via `sys.executable -m yt_dlp` ou API Python, isoler les dossiers de téléchargement, éviter le fallback erroné | M2 | Survey |
| 5 | VTT Caption Deduplication | Dédupliquer les sous-titres YouTube auto-générés à fenêtres roulantes dans `transcriber.py` | M2 | Survey |
| 6 | Highlight Detection French NLP | Gérer l'élision (`l'`, `d'`) et le pluriel (`s`, `x`) pour détecter les mots-clés prophétiques (`miracles`, `prières`, `bénédictions`) | M2 | Survey |
| 7 | FFmpeg Render & Visual Gospel Theme | Optimiser le rendu CPU (downscale avant blur), sécuriser `ass_path`, emoji cleaning, et ajuster la marge droite `MarginR=140` | M2 | Survey |
| 8 | Prophetic Hooks Validation | Valider les 8 accroches prophétiques chrétiennes et leur déclenchement contextuel | M3 | Survey |
| 9 | Viral Captions & AMEN CTA | Valider la description multi-niveaux et l'appel à l'action "Écris AMEN en commentaire" | M3 | Survey |
| 10 | Ivory Coast Geotargeting & GMT | Valider les 10 hashtags (#chretien #cotedivoire #abidjan #foi) et les 4 créneaux horaires Abidjan GMT | M3 | Survey |
| 11 | End-to-End Pipeline Integration | Valider le pipeline complet de bout en bout (`main.py --demo` et mode production) avec génération vidéo, payload TikTok et notification | M4 | Survey |
| 12 | Comprehensive E2E Testing Suite | Suite de tests automatisés Tiers 1-4 sous `tests/` avec runner autonome | E2E Track | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | DevOps-Bot & Pipeline Core | Fix P0 KeyError, implémenter upload PUT binaire TikTok, sécuriser GitHub Actions workflow, créer workflow CI | None | DONE |
| M2 | Media-Bot Pipeline Hardening | Résilience downloader yt-dlp, déduplication VTT, matching NLP pluriels/élisions, optimisation FFmpeg & marge Safe Zone | M1 | DONE |
| M3 | Growth-Bot Validation | Validation accroches prophétiques, descriptions AMEN, hashtags Abidjan & créneaux GMT | M1 | DONE |
| M4 | End-to-End Pipeline Integration | Exécution autonome complète de A à Z (vidéo synthétique + pipeline standard), vérification des artefacts générés | M1, M2, M3 | DONE |
| E2E | E2E Testing Suite (Dual Track) | Suite de tests complète Tiers 1-4 couvrant toutes les fonctionnalités de l'inventaire | None | DONE |

## Code Layout
```
/home/antigravity/digrekarlito11-eng/tiktok-autopilot/
├── .github/
│   └── workflows/
│       ├── generate_tiktok.yml  # Workflow de production
│       └── ci.yml               # Workflow d'intégration continue
├── src/
│   ├── __init__.py
│   ├── clip_extractor.py        # Media-Bot : Découpage & scoring
│   ├── downloader.py            # Media-Bot : Téléchargement yt-dlp
│   ├── growth_optimizer.py      # Growth-Bot : Accroches, descriptions, tags, GMT
│   ├── notifier.py              # DevOps-Bot : Webhooks Discord/Telegram
│   ├── pipeline.py              # Orchestration des 3 bots
│   ├── themes.py                # Media-Bot : Thèmes visuels (gospel, etc.)
│   ├── tiktok_publisher.py      # DevOps-Bot : Publication API v2
│   ├── transcriber.py           # Media-Bot : Whisper / VTT
│   └── video_formatter.py       # Media-Bot : FFmpeg 9:16 vertical & ASS
├── tests/                       # E2E & Unit Test Track
│   ├── conftest.py
│   ├── test_devops_bot.py
│   ├── test_media_bot.py
│   ├── test_growth_bot.py
│   ├── test_adversarial_m1.py
│   ├── test_devops_bot_stress.py
│   ├── test_adversarial_media_bot.py
│   ├── test_challenger_m2_render.py
│   └── test_e2e_pipeline.py
├── main.py                      # Point d'entrée CLI
└── requirements.txt
```

## Interface Contracts
### Media-Bot ↔ Growth-Bot
- `ClipExtractor.extract_highlights()` retourne une liste de dictionnaires `{start, end, duration, score, text, matched_keywords}`.
- `GrowthOptimizer.generate_growth_package(clip_text, video_title)` prend `clip_text` et `video_title`, et retourne un dictionnaire contenant :
  - `hook_banner`: str (Accroche prophétique)
  - `caption`: str (Description avec CTA "Écris AMEN...")
  - `hashtags`: list[str] (10 hashtags ciblés)
  - `recommended_slots`: list[str] (Créneaux GMT Abidjan)
  - `location_focus`: str ("Côte d'Ivoire (GMT / Abidjan) & Diaspora")
  - `target_audience`: str

### Media-Bot ↔ VideoFormatter
- `VideoFormatter.create_tiktok_clip(video_path, clip_meta, output_path, theme, watermark, progress_bar)` prend le fichier source et les métadonnées du clip avec `hook_banner`, et produit une vidéo MP4 1080x1920 (9:16) conforme.

### Pipeline ↔ TikTokPublisher
- `TikTokPublisher.publish_clip(video_path, post_caption, privacy_level)` prend la vidéo MP4 finale et la légende, génère le payload JSON, appelle l'API v2 d'initialisation, puis téléverse le flux binaire via HTTP PUT vers l'URL retournée.
