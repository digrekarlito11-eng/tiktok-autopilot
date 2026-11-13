# Infrastructure de Test : tiktok-autopilot

## 1. Vue d'Ensemble

La suite de tests de `tiktok-autopilot` est une infrastructure de tests automatisés conçue selon la méthodologie en **4 Paliers (4 Tiers)**.
Elle valide l'intégrité fonctionnelle, algorithmique et visuelle des trois bots modulaires :
- **DevOps-Bot** : Orchestration GitHub Actions, point d'entrée CLI `main.py`, publication TikTok API v2 (`src/tiktok_publisher.py`), notifications webhook (`src/notifier.py`).
- **Media-Bot** : Téléchargement `yt-dlp` (`src/downloader.py`), transcription & VTT (`src/transcriber.py`), scoring viral & découpage (`src/clip_extractor.py`), composition vidéo 9:16 vertical 1080x1920 avec fond flou et sous-titres dynamiques ASS (`src/video_formatter.py`, `src/themes.py`).
- **Growth-Bot** : Accroches prophétiques chrétiennes (`src/growth_optimizer.py`), description avec appel à l'action viral AMEN, hashtags ultra-ciblés Côte d'Ivoire & diaspora, créneaux GMT Abidjan, fiches récapitulatives.

---

## 2. Taxonomie des Tests (4 Paliers)

| Palier | Scope | Fichiers de Tests Dédiés | Description & Objectifs |
|---|---|---|---|
| **Tier 1** | Couverture Fonctionnelle Isolée | `tests/test_growth_bot.py`<br>`tests/test_media_bot.py`<br>`tests/test_devops_bot.py` | Validation unitaire et opaque-box de chaque brique : 8 accroches prophétiques, CTA AMEN, 10 hashtags géo-ciblés, parsing VTT, scoring de fluidité/mots-clés, thèmes graphiques (Gospel or céleste), formatage temporel ASS, initialisation TikTok API v2, parsing CLI. |
| **Tier 2** | Limites & Cas aux Bornes | `tests/test_growth_bot.py`<br>`tests/test_media_bot.py`<br>`tests/test_devops_bot.py` | Résilience face aux anomalies : chaînes vides, segments textuels vierges, vidéos très courtes (<10s) déclenchant le fallback sécurisé, caractères spéciaux, apostrophes et élisions françaises (`l'onction`, `d'amour`), absence de variables d'environnement (`TIKTOK_ACCESS_TOKEN`, `TIKTOK_WEBHOOK_URL`), tolérance aux clés manquantes dans les packages d'export. |
| **Tier 3** | Interactions Inter-Composants | `tests/test_e2e_pipeline.py` | Validation des contrats d'interface :<br>1. Media-Bot `ClipExtractor` ➔ Growth-Bot `GrowthOptimizer`<br>2. Thème Gospel : harmonisation chromatique or céleste (`&H0000D7FF&`) entre les sous-titres ASS et la barre de progression FFmpeg (`0xFFD700`)<br>3. Positionnement du filigrane `@parole.de.foi` dans la Safe Zone TikTok (`MarginL=45, MarginV=210`)<br>4. Pipeline ➔ TikTokPublisher API v2 (génération du JSON `post_info` et `source_info`). |
| **Tier 4** | Scénarios Métier Réels (Prédication Karl) | `tests/test_e2e_pipeline.py` | Simulation de bout en bout de l'expérience autonome de Karl à Abidjan : exécution complète du pipeline avec génération de vidéo synthétique et sous-titres de prédication, vérification de la création effective de la vidéo MP4 9:16 (1080x1920), de la fiche de stratégie `FICHE_TIKTOK_*.txt`, du payload `*_tiktok_payload.json` et du manifeste d'exécution `tiktok_results.json`. Validation également de `python main.py --demo`. |

---

## 3. Architecture des Fichiers de Test

```
tests/
├── conftest.py            # Fixtures partagées : isolation d'environnement, répertoires temporaires,
│                          # segments de transcription de test, fixtures VTT standard & rolling,
│                          # générateur rapide de vidéo synthétique MP4 via FFmpeg lavfi.
├── test_devops_bot.py     # Tests unitaires DevOps-Bot : CLI main.py, TikTokPublisher (Init + PUT upload binaire),
│                          # Notifier mobile webhook, gestion des pannes réseau.
├── test_growth_bot.py     # Tests unitaires Growth-Bot : 8 hooks prophétiques, description AMEN,
│                          # 10 hashtags Abidjan/Foi, créneaux GMT, calcul de rétention, résilience export.
├── test_media_bot.py      # Tests unitaires Media-Bot : parsing VTT et nettoyage HTML, scoring viral,
│                          # thèmes graphiques, timestamps ASS, rendu vidéo FFmpeg 9:16.
└── test_e2e_pipeline.py   # Tests d'intégration Tier 3 & Tier 4 : contrats d'interface, Safe Zones,
                           # exécution autonome A à Z simulant le flux de prédication chrétienne.
```

---

## 4. Stratégie d'Isolation et Déterminisme

1. **Zéro dépendance réseau externe** : Les tests ne dépendent pas des serveurs de YouTube ni de l'API live de TikTok. Les appels HTTP externes (`urllib.request.urlopen`) sont isolés ou simulés avec des mocks dédiés.
2. **Génération synthétique ultra-rapide** : Plutôt que de manipuler des fichiers vidéo réels lourds, `conftest.py` utilise un filtre synthétique FFmpeg (`lavfi testsrc` et `sine`) générant une vidéo test 16:9 de 5 secondes en moins de 0.3 seconde.
3. **Isolation filesystem hermétique** : Chaque test écrivant des fichiers utilise la fixture standard `tmp_path` de pytest, évitant toute pollution du dossier de travail ou de git.
4. **Environnement propre** : La fixture autouse `clean_test_env` réinitialise les variables d'environnement `TIKTOK_ACCESS_TOKEN` et `TIKTOK_WEBHOOK_URL` avant chaque test.

---

## 5. Exécution des Tests

### Lancer l'ensemble de la suite :
```bash
.venv/bin/pytest tests/ -v
```

### Lancer un module spécifique :
```bash
# Tests Growth-Bot (Hooks prophétiques, hashtags, créneaux GMT)
.venv/bin/pytest tests/test_growth_bot.py -v

# Tests Media-Bot (VTT, découpage, FFmpeg 9:16, thèmes)
.venv/bin/pytest tests/test_media_bot.py -v

# Tests DevOps-Bot (Publication TikTok API v2, upload PUT, webhook, CLI)
.venv/bin/pytest tests/test_devops_bot.py -v

# Tests d'Intégration et E2E Pipeline (Tier 3 & Tier 4)
.venv/bin/pytest tests/test_e2e_pipeline.py -v
```
