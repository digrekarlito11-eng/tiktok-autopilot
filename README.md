# 📱 TikTok Autopilot — Usine Vidéo Automatisée

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Cloud%20100%25%20Gratuit-success?logo=github)](.github/workflows/generate_tiktok.yml)
[![TikTok Format](https://img.shields.io/badge/Format-9%3A16%20Vertical%201080x1920-fe2c55?logo=tiktok)](https://tiktok.com)
[![Status](https://img.shields.io/badge/Statut-Op%C3%A9rationnel%20%2F%20Production-brightgreen)](#)
[![Owner](https://img.shields.io/badge/Propri%C3%A9taire-Karl-orange)](#)

> **TikTok Autopilot** est le système automatisé de découpage, recadrage et habillage vidéo conçu pour la **Société Autonome de Karl**. Il transforme des vidéos longues (interviews, podcasts, conférences) en clips TikTok viraux haute rétention au format 9:16, avec sous-titres dynamiques et fiche de publication prête à l'emploi.

---

## 🎯 Comment Ça Marche (En 3 Secondes)

```text
🔗 Tu donnes un lien (YouTube, podcast, interview...)
                          │
                          ▼
            🤖 L'ÉQUIPE AUTONOME S'ACTIVE :
            1. DevOps-Bot télécharge et prépare le flux dans le Cloud
            2. Media-Bot détecte la punchline (30-60s) & formate en 9:16
            3. Growth-Bot génère le Hook, la Description & les Hashtags
                          │
                          ▼
📦 Tu télécharges un pack complet prêt à poster :
   ├── 🎬 Vidéo 9:16 verticale HD avec fond flouté et sous-titres dynamiques
   ├── 📝 FICHE_TIKTOK.txt (Accroche + Description + Hashtags)
   └── 📊 Score de viralité et de rétention
```

---

## 🚀 2 Façons Simples de l'Utiliser

### Option 1 : Directement depuis ton Téléphone ou Ordinateur (Zéro Installation)
> **Recommandé pour Karl** : Tout tourne dans le Cloud de GitHub sans toucher à aucun terminal.

1. Rends-toi sur l'onglet **Actions** de ce dépôt GitHub.
2. Clique sur **"🚀 Usine de Production Vidéo TikTok"**.
3. Clique sur **"Run workflow"**, colle le lien de ta vidéo et valide.
4. Au bout de 2 minutes, récupère ton archive ZIP contenant la vidéo finale et la fiche mémo !

---

### Option 2 : Sur ton Ordinateur en Ligne de Commande

#### 1. Lancer la démo instantanée
```bash
python main.py --demo
```

#### 2. Générer un TikTok depuis un lien
```bash
python main.py --url "https://www.youtube.com/watch?v=XXXXX" --clips 1
```

#### 3. Générer depuis une vidéo locale sur ton disque
```bash
python main.py --video "mes_videos/interview.mp4" --clips 2
```

---

## 📂 Contenu du Pack Final Généré (Dans `/output`)

Chaque extraction produit :
1. **`tiktok_clip_1.mp4`** : Vidéo $1080 \times 1920$ (9:16) haute définition :
   - Fond d'écran flouté et immersif.
   - Vidéo d'origine nette et centrée.
   - Bannière d'accroche (Hook) dans la *Safe Zone* supérieure.
   - Sous-titres dynamiques avec mots mis en avant au centre-bas.
2. **`FICHE_TIKTOK_clip_1.txt`** : Tout le texte prêt à copier-coller dans l'application TikTok (légende, appel à l'action, hashtags ciblés).
3. **`tiktok_results.json`** : Données techniques et scores de rétention.

---

## 🛡️ Les 3 Sous-Agents Dédiés à TikTok

| Sous-Agent | Responsabilité principale |
| :--- | :--- |
| 🤖 **DevOps-Bot** | Gère GitHub Actions, les dépendances Python, l'exécution sans serveur et l'archivage sécurisé. |
| 🎬 **Media-Bot** | Gère le découpage, le calcul de rythme, l'encodage FFmpeg 9:16 et l'animation des sous-titres. |
| 📈 **Growth-Bot** | Optimise le titre d'accroche (3 premières secondes), le SEO TikTok et la sélection des hashtags viraux. |

---

*Projet sous la direction du CEO & Orchestrateur de la Société Autonome — Propriété exclusive de Karl.*
