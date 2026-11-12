# 📱 TikTok Autopilot — Usine Vidéo Automatisée

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Cloud%20100%25%20Gratuit-success?logo=github)](.github/workflows/generate_tiktok.yml)
[![TikTok Format](https://img.shields.io/badge/Format-9%3A16%20Vertical%201080x1920-fe2c55?logo=tiktok)](https://tiktok.com)
[![Status](https://img.shields.io/badge/Statut-Op%C3%A9rationnel%20%2F%20Production-brightgreen)](#)
[![Owner](https://img.shields.io/badge/Propri%C3%A9taire-Karl-orange)](#)
[![Ecosystem](https://img.shields.io/badge/Karl%20Studio-Ecosyst%C3%A8me%20Connect%C3%A9-blue)](https://digrekarlito11-eng.github.io/karl-studio/)

> **TikTok Autopilot** est la plateforme autonome de découpage, recadrage, habillage et optimisation vidéo conçue pour la **Société Autonome de Karl**. Elle transforme des vidéos longues en clips TikTok verticaux 9:16 viraux haute rétention, aux couleurs de la marque Karl Studio, avec sous-titres dynamiques mot-à-mot et fiches de publication prêtes à l'emploi.

---

## 🎯 Comment Ça Marche (En 3 Secondes)

```text
🔗 Tu donnes un lien (YouTube, podcast, interview...)
                          │
                          ▼
            🤖 L'ÉQUIPE AUTONOME S'ACTIVE :
            1. DevOps-Bot télécharge et prépare le flux dans le Cloud
            2. Media-Bot détecte la punchline (30-60s), recadre en 9:16
               applique le Thème (Gold, Neon, Minimal) & la barre animée
            3. Growth-Bot génère le Hook, la Description & les Hashtags
                          │
                          ▼
📦 Tu télécharges ton pack TikTok prêt à poster :
   ├── 🎬 Vidéo 9:16 HD (Fond flou + vidéo nette + Watermark @karlstudio + Barre de progression)
   ├── 📝 FICHE_TIKTOK.txt (Hook + Description + Hashtags + Meilleurs horaires de publication)
   └── 📊 Données de rétention et redirection vers Karl Studio
```

---

## 🎨 Les 3 Thèmes Graphiques Karl Studio

| Thème | Ambiance & Palette | Recommandé pour |
| :--- | :--- | :--- |
| 👑 **`gold`** *(Défaut)* | **Dark Luxury Karl Studio** : Bannière or éclatant, sous-titres blancs perle et barre de progression dorée. | Podcasts business, mindset, interviews prestigieuses. |
| ⚡ **`neon`** | **Cyber Neon Viral** : Accroche vert néon électrisant, surbrillance cyan, dynamisme maximal. | Sujets choc, astuces rapides, punchlines courtes. |
| 🎬 **`minimal`** | **Cinematic Clean** : Blanc pur et contour cinéma sobre et élégant. | Masterclasses, sessions de création musicale au studio. |

---

## 🚀 2 Façons Simples de l'Utiliser

### Option 1 : Directement depuis ton Téléphone ou Ordinateur (Recommandé)
> Tout tourne dans le Cloud de GitHub sans toucher à aucun terminal ni payer de serveur.

1. Rends-toi sur l'onglet **Actions** de ce dépôt : **[Lancer la Machine TikTok](https://github.com/digrekarlito11-eng/tiktok-autopilot/actions)**.
2. Clique sur **"🚀 Usine de Production Vidéo TikTok"**.
3. Clique sur **"Run workflow"** :
   - Colle le lien de la vidéo longue.
   - Choisis le thème (`gold`, `neon`, `minimal`).
   - Choisis ton identifiant de marque (par défaut : `@karlstudio`).
4. Valide et récupère ton archive ZIP prête à publier !

---

### Option 2 : Sur ton Ordinateur en Ligne de Commande

#### 1. Lancer la démo instantanée
```bash
python main.py --demo --theme gold
```

#### 2. Générer un TikTok avec options personnalisées
```bash
python main.py --url "https://www.youtube.com/watch?v=XXXXX" --clips 1 --theme gold --watermark "@karlstudio"
```

#### 3. Traiter une liste de vidéos en rafale (Mode Batch)
Crée un fichier `mes_liens.txt` avec plusieurs URLs et lance :
```bash
python main.py --batch mes_liens.txt --clips 2 --theme neon
```

---

## 📂 Contenu du Pack Final Généré (Dans `/output`)

Chaque vidéo produite comprend :
1. **`tiktok_*.mp4`** : Vidéo $1080 \times 1920$ (9:16) haute définition :
   - Fond flouté élégant.
   - Vidéo d'origine parfaitement proportionnée et centrée.
   - Badge `@karlstudio` dans la zone de sécurité supérieure gauche.
   - Titre d'accroche (Hook) captivant en haut.
   - Sous-titres dynamiques mot-à-mot avec surbrillance colorée au centre-bas.
   - Barre de progression animée ultra-fluide tout en bas.
2. **`FICHE_TIKTOK_*.txt`** : Tout le texte prêt à être copié-collé dans TikTok (légende avec émojis, appel à l'action vers Karl Studio, hashtags ciblés et créneaux horaires idéaux).
3. **`tiktok_results.json`** : Bilan chiffré des scores d'attention.

---

*Projet sous la direction du CEO & Orchestrateur de la Société Autonome — Propriété exclusive de Karl.*
