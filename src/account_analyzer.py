"""
Agent Autonome d'Analyse de Compte TikTok 24/7 (Account Analyzer Bot).
Tourne en ligne sur GitHub Actions sans coût d'API (0 crédit consommé).

Mission :
1. Se connecter en lecture seule à TikTok Studio (via TIKTOK_SESSION_ID) et relever
   les performances réelles des vidéos publiées (vues, j'aime, commentaires, confidentialité, durée).
2. Diagnostiquer automatiquement les causes du manque de vues et de commentaires
   (rafale de publications, vidéos en examen, durée trop longue, accroches répétitives,
   absence de question ouverte en commentaire, etc.).
3. Historiser l'évolution dans `history/account_analytics.json`.
4. Produire des recommandations exploitables par `GrowthOptimizer` dans
   `history/growth_recommendations.json` et un rapport clair en français dans
   `history/ACCOUNT_HEALTH_REPORT.md`.
"""

import argparse
import datetime
import json
import os
import re
import statistics
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from src.growth_optimizer import GrowthOptimizer
from src.notifier import TikTokNotifier
from src.tiktok_studio_uploader import TikTokStudioUploader

ANALYTICS_HISTORY_PATH = "history/account_analytics.json"
RECOMMENDATIONS_PATH = "history/growth_recommendations.json"
HEALTH_REPORT_PATH = "history/ACCOUNT_HEALTH_REPORT.md"
PROCESSED_VIDEOS_PATH = "history/processed_videos.json"

COMMENT_MAGNET_ROTATION: List[str] = [
    "Écris 'AMEN' en commentaire et partage ce message à quelqu'un qui en a besoin 👇🙏",
    "Quelle phrase de cette parole t'a le plus touché aujourd'hui ? Dis-le en commentaire 👇📖",
    "Si tu crois que Dieu agit dans ta saison, écris 'JE REÇOIS' en commentaire 🔥👇",
    "Envoie cette vidéo à un proche et écris 'GLOIRE À DIEU' en commentaire 🕊️👇",
]


def parse_metric_number(raw: Any) -> int:
    """Convertit un compteur TikTok localisé ('1,2K', '3.5M', '1 250', '0') en entier."""
    if isinstance(raw, (int, float)):
        return max(0, int(raw))
    text = str(raw or "").strip().upper().replace("\u00a0", "").replace(" ", "")
    if not text or text in {"-", "--", "N/A"}:
        return 0
    m = re.match(r"^(\d+(?:[.,]\d+)?)([KMB])?$", text)
    if not m:
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else 0
    val = float(m.group(1).replace(",", "."))
    suffix = m.group(2)
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)
    return int(round(val * mult))


def parse_duration_seconds(raw: Any) -> Optional[int]:
    """Convertit une durée 'MM:SS' ou 'HH:MM:SS' en secondes."""
    text = str(raw or "").strip()
    m = re.match(r"^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})$", text)
    if not m:
        return None
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2))
    seconds = int(m.group(3))
    return hours * 3600 + minutes * 60 + seconds


def parse_studio_row_text(row_text: str) -> Optional[Dict[str, Any]]:
    """
    Extrait les champs structurés d'une ligne de publication TikTok Studio.
    Exemple typique de lignes :
      01:59
      📖 Dieu alléluia en être en harmonie...
      15 nov., 13:48
      Tout le monde
      0
      0
      0
    """
    lines = [ln.strip() for ln in (row_text or "").splitlines() if ln.strip()]
    if len(lines) < 4:
        return None

    duration_str = ""
    duration_sec: Optional[int] = None
    content_lines: List[str] = []
    date_str = ""
    privacy = ""
    numeric_tokens: List[int] = []

    date_re = re.compile(
        r"^(?:\d{1,2}\s+[a-zéûôàîç]+\.?,\s*\d{1,2}:\d{2}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|aujourd'hui.*|hier.*|il y a\s+\d+.*)$",
        re.IGNORECASE,
    )
    privacy_re = re.compile(
        r"(tout le m|public|everyone|amis|friends|moi uniquement|only me|priv[ée]|examen|review)",
        re.IGNORECASE,
    )
    metric_re = re.compile(r"^\d+(?:[.,]\d+)?\s*[KMBkmb]?$")

    for ln in lines:
        if not duration_str and parse_duration_seconds(ln) is not None:
            duration_str = ln
            duration_sec = parse_duration_seconds(ln)
            continue
        if not date_str and len(ln) <= 35 and date_re.match(ln):
            date_str = ln
            continue
        if not privacy and len(ln) <= 40 and privacy_re.search(ln):
            privacy = ln
            continue
        if metric_re.match(ln.replace("\u00a0", "").replace(" ", "")):
            numeric_tokens.append(parse_metric_number(ln))
            continue
        content_lines.append(ln)

    title = " ".join(content_lines).strip()
    if not title and not date_str:
        return None

    # Les 3 derniers compteurs numériques d'une ligne Studio sont : Vues, J'aime, Commentaires
    if len(numeric_tokens) >= 3:
        views, likes, comments = numeric_tokens[-3], numeric_tokens[-2], numeric_tokens[-1]
    elif len(numeric_tokens) == 2:
        views, likes, comments = numeric_tokens[0], numeric_tokens[1], 0
    elif len(numeric_tokens) == 1:
        views, likes, comments = numeric_tokens[0], 0, 0
    else:
        views, likes, comments = 0, 0, 0

    return {
        "title": title[:160],
        "date": date_str,
        "duration": duration_str,
        "duration_seconds": duration_sec,
        "privacy": privacy or "Inconnu",
        "views": views,
        "likes": likes,
        "comments": comments,
    }


def _extract_minute_timestamps(videos: List[Dict[str, Any]]) -> List[int]:
    """Extrait les horodatages HH:MM (en minutes depuis minuit) pour détecter les rafales."""
    minutes: List[int] = []
    for v in videos:
        m = re.search(r"(\d{1,2}):(\d{2})", str(v.get("date") or ""))
        if m:
            minutes.append(int(m.group(1)) * 60 + int(m.group(2)))
    return sorted(minutes)


def _detect_burst_posting(videos: List[Dict[str, Any]], processed_videos: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Détecte si trop de vidéos ont été publiées en rafale sur quelques minutes."""
    # Regrouper par date (jour) si disponible
    by_day: Dict[str, List[int]] = {}
    for v in videos:
        date_str = str(v.get("date") or "")
        m = re.search(r"(\d{1,2}):(\d{2})", date_str)
        if not m:
            continue
        day_key = re.sub(r",?\s*\d{1,2}:\d{2}.*$", "", date_str).strip().lower() or "recent"
        by_day.setdefault(day_key, []).append(int(m.group(1)) * 60 + int(m.group(2)))

    for day_key, mins in by_day.items():
        mins.sort()
        for i in range(len(mins)):
            window = [t for t in mins if mins[i] <= t <= mins[i] + 30]
            if len(window) >= 4:
                return (
                    True,
                    f"{len(window)} vidéos publiées en moins de 30 minutes ({day_key}). "
                    "Sur TikTok, envoyer beaucoup de vidéos en rafale déclenche souvent un frein anti-spam (0 vue).",
                )

    # Repli : vérifier le registre des cycles récents
    if processed_videos:
        last_entry = processed_videos[-1]
        clips_pub = int(last_entry.get("clips_published") or 0)
        if clips_pub >= 8:
            return (
                True,
                f"Le dernier cycle a publié {clips_pub} vidéos d'affilée en un seul passage. "
                "Espacer les publications (2 à 3 par jour) évite le bridage de l'algorithme.",
            )

    return False, ""


def _detect_repetitive_hooks(processed_videos: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Détecte si trop de clips récents utilisent exactement la même accroche."""
    recent_hooks: List[str] = []
    for entry in processed_videos[-3:]:
        for clip in entry.get("clips_summary") or []:
            hook = str(clip.get("hook") or "").strip()
            if hook:
                recent_hooks.append(hook)
    if len(recent_hooks) < 5:
        return False, ""
    most_common_hook, count = Counter(recent_hooks).most_common(1)[0]
    ratio = count / len(recent_hooks)
    if ratio >= 0.45:
        pct = int(round(ratio * 100))
        return (
            True,
            f"L'accroche « {most_common_hook} » revient sur {pct}% des derniers clips ({count}/{len(recent_hooks)}). "
            "Varier l'accroche visuelle sur chaque extrait augmente le taux de clic et les commentaires.",
        )
    return False, ""


def diagnose_account(
    snapshot: Dict[str, Any],
    previous_snapshots: Optional[List[Dict[str, Any]]] = None,
    processed_videos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Moteur de diagnostic 100% déterministe (0 crédit API).
    Analyse les métriques du compte et produit :
    - kpis : indicateurs chiffrés + tendance par rapport au relevé précédent
    - diagnostics : liste ordonnée des causes probables du manque de vues / commentaires
    - action_plan : plan d'action priorisé et concret
    - recommendations : paramètres exploitables automatiquement par GrowthOptimizer
    """
    previous_snapshots = previous_snapshots or []
    processed_videos = processed_videos or []
    videos: List[Dict[str, Any]] = snapshot.get("videos") or []

    views_list = [int(v.get("views") or 0) for v in videos]
    likes_list = [int(v.get("likes") or 0) for v in videos]
    comments_list = [int(v.get("comments") or 0) for v in videos]
    durations = [v["duration_seconds"] for v in videos if isinstance(v.get("duration_seconds"), int)]

    total_views = sum(views_list)
    total_likes = sum(likes_list)
    total_comments = sum(comments_list)
    analyzed_count = len(videos)
    avg_views = round(total_views / analyzed_count, 1) if analyzed_count else 0.0
    median_views = round(float(statistics.median(views_list)), 1) if views_list else 0.0
    zero_view_count = sum(1 for x in views_list if x == 0)
    zero_view_ratio = round(zero_view_count / analyzed_count, 3) if analyzed_count else 0.0
    avg_duration_sec = round(sum(durations) / len(durations), 1) if durations else 0.0

    like_rate_pct = round((total_likes / total_views) * 100, 2) if total_views > 0 else 0.0
    comment_rate_pct = round((total_comments / total_views) * 100, 2) if total_views > 0 else 0.0

    # Évolution par rapport au relevé précédent
    delta_views = 0
    delta_likes = 0
    delta_comments = 0
    if previous_snapshots:
        prev_kpis = previous_snapshots[-1].get("kpis") or {}
        delta_views = total_views - int(prev_kpis.get("total_views") or 0)
        delta_likes = total_likes - int(prev_kpis.get("total_likes") or 0)
        delta_comments = total_comments - int(prev_kpis.get("total_comments") or 0)

    # Top vidéos (triées par vues puis commentaires)
    top_videos = sorted(
        videos,
        key=lambda v: (int(v.get("views") or 0), int(v.get("comments") or 0), int(v.get("likes") or 0)),
        reverse=True,
    )[:5]

    diagnostics: List[Dict[str, str]] = []
    action_plan: List[str] = []

    # 1. Vérifier les vidéos en examen ou privées
    restricted = [
        v for v in videos
        if re.search(r"(moi uniquement|only me|priv[ée]|examen|review)", str(v.get("privacy") or ""), re.IGNORECASE)
    ]
    if restricted:
        diagnostics.append({
            "code": "privacy_or_review_hold",
            "severity": "haute",
            "title": "Vidéos restreintes ou en cours d'examen",
            "detail": f"{len(restricted)}/{analyzed_count} vidéo(s) ne sont pas encore visibles par « Tout le monde ».",
        })
        action_plan.append(
            "Vérifier dans TikTok Studio que les vidéos bloquées en « Moi uniquement » passent bien en « Tout le monde »."
        )

    # 2. Détection des rafales de publication
    is_burst, burst_detail = _detect_burst_posting(videos, processed_videos)
    if is_burst:
        diagnostics.append({
            "code": "burst_posting",
            "severity": "critique",
            "title": "Publication en rafale (risque de frein anti-spam TikTok)",
            "detail": burst_detail,
        })
        action_plan.append(
            "Espacer les publications : passer à 2 ou 3 Shorts par cycle (matin 06h, midi 13h, soir 19h GMT) au lieu de 10 d'affilée."
        )

    # 3. Mur des 0 vues / portée très faible
    if analyzed_count >= 3 and zero_view_ratio >= 0.7:
        diagnostics.append({
            "code": "zero_views_wall",
            "severity": "critique",
            "title": "Plafond à 0 vue sur la majorité des vidéos",
            "detail": f"{zero_view_count}/{analyzed_count} vidéos analysées sont à 0 vue. "
            "C'est typique d'un compte récent qui publie uniquement via navigateur sans activité humaine sur téléphone ou après une rafale.",
        })
        action_plan.append(
            "Chauffer le compte 5 min/jour depuis le téléphone : regarder, liker et commenter 5 à 10 vidéos chrétiennes francophones (Yvan Castanou, Marcelo Tunasi, Mohamed Sanogo, etc.)."
        )
    elif analyzed_count >= 3 and avg_views < 200:
        diagnostics.append({
            "code": "low_initial_reach",
            "severity": "moyenne",
            "title": "Portée initiale encore faible (< 200 vues moyennes)",
            "detail": f"Moyenne actuelle : {avg_views} vues/vidéo (médiane : {median_views}). "
            "L'algorithme n'a pas encore assez de signaux de rétention dans les 3 premières secondes.",
        })
        action_plan.append(
            "Renforcer les 3 premières secondes (phrase choc immédiate) et utiliser les 3 nouveaux packs de 5 hashtags chrétiens ciblés."
        )

    # 4. Durée moyenne élevée vs rétention
    if avg_duration_sec >= 105 and avg_views < 300:
        diagnostics.append({
            "code": "long_clips_retention",
            "severity": "moyenne",
            "title": "Clips proches de 2 minutes difficiles à finir sur un compte jeune",
            "detail": f"Durée moyenne mesurée : {int(avg_duration_sec)}s (~{int(avg_duration_sec // 60)}m{int(avg_duration_sec % 60):02d}s). "
            "Tant que l'audience n'est pas installée, les clips de 45 à 75 secondes obtiennent un bien meilleur taux de visionnage complet.",
        })
        action_plan.append(
            "Tester des extraits plus courts (45 à 75 secondes) centrés sur une seule vérité biblique percutante."
        )

    # 5. Manque de commentaires
    if analyzed_count > 0 and (total_comments == 0 or (total_views >= 100 and comment_rate_pct < 1.0)):
        diagnostics.append({
            "code": "low_comments",
            "severity": "haute",
            "title": "Absence ou faiblesse des commentaires",
            "detail": f"Total commentaires : {total_comments} (taux : {comment_rate_pct}%). "
            "Sur TikTok chrétien, les commentaires ('AMEN', témoignages, questions) sont le carburant principal du fil Pour Toi.",
        })
        action_plan.append(
            "Épingler un commentaire-question juste après publication et répondre aux 3 premiers commentaires dans les 30 minutes."
        )

    # 6. Accroches répétitives
    is_rep, rep_detail = _detect_repetitive_hooks(processed_videos)
    if is_rep:
        diagnostics.append({
            "code": "repetitive_hooks",
            "severity": "moyenne",
            "title": "Accroches visuelles trop répétitives",
            "detail": rep_detail,
        })
        action_plan.append(
            "Varier les titres d'accroche d'un clip à l'autre pour éviter que l'audience croie revoir la même vidéo."
        )

    if not diagnostics:
        diagnostics.append({
            "code": "healthy_growth",
            "severity": "info",
            "title": "Croissance saine détectée",
            "detail": f"{total_views} vues et {total_comments} commentaires sur les {analyzed_count} dernières vidéos.",
        })
        action_plan.append(
            "Continuer la cadence régulière avec les 3 packs de hashtags chrétiens et doubler les thèmes des vidéos les plus vues."
        )

    # Rotation automatique du CTA pour le prochain cycle GrowthOptimizer
    rotation_idx = len(previous_snapshots) % len(COMMENT_MAGNET_ROTATION)
    recommended_cta = COMMENT_MAGNET_ROTATION[rotation_idx]

    status = "critique" if any(d["severity"] == "critique" for d in diagnostics) else (
        "attention" if any(d["severity"] in ("haute", "moyenne") for d in diagnostics) else "sain"
    )

    kpis = {
        "publications_count": snapshot.get("publications_count", analyzed_count),
        "drafts_count": snapshot.get("drafts_count", 0),
        "analyzed_videos_count": analyzed_count,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "avg_views": avg_views,
        "median_views": median_views,
        "zero_view_count": zero_view_count,
        "zero_view_ratio": zero_view_ratio,
        "avg_duration_seconds": avg_duration_sec,
        "like_rate_pct": like_rate_pct,
        "comment_rate_pct": comment_rate_pct,
        "delta_views": delta_views,
        "delta_likes": delta_likes,
        "delta_comments": delta_comments,
    }

    recommendations = {
        "updated_at": snapshot.get("timestamp") or datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "account_status": status,
        "recommended_cta": recommended_cta,
        "recommended_clips_per_cycle": 3 if is_burst else 5,
        "recommended_clip_duration_seconds": [45, 75] if avg_duration_sec >= 105 and avg_views < 300 else [60, 115],
        "hashtag_packs": GrowthOptimizer.HASHTAG_PACKS,
        "active_alerts": [d["code"] for d in diagnostics if d["severity"] in ("critique", "haute")],
    }

    return {
        "status": status,
        "kpis": kpis,
        "diagnostics": diagnostics,
        "action_plan": action_plan,
        "top_videos": top_videos,
        "recommendations": recommendations,
    }


def generate_health_report_markdown(analysis: Dict[str, Any], timestamp: str) -> str:
    """Génère un rapport clair en français, sans jargon, pour Karl."""
    kpis = analysis["kpis"]
    status_badges = {
        "critique": "🔴 Action prioritaire requise",
        "attention": "🟠 À optimiser",
        "sain": "🟢 Compte en bonne dynamique",
    }
    badge = status_badges.get(analysis.get("status", ""), "ℹ️ Analyse")

    def _fmt_delta(val: int) -> str:
        if val > 0:
            return f" (+{val})"
        if val < 0:
            return f" ({val})"
        return ""

    lines = [
        "# 📊 Rapport Santé & Croissance TikTok 24/7 — Karl",
        "",
        f"- **Dernière analyse :** {timestamp}",
        f"- **État du compte :** {badge}",
        f"- **Vidéos publiées (TikTok Studio) :** {kpis['publications_count']} (Brouillons : {kpis['drafts_count']})",
        f"- **Vidéos analysées sur ce relevé :** {kpis['analyzed_videos_count']}",
        "",
        "## 📈 Chiffres clés",
        f"- **Vues cumulées (échantillon) :** {kpis['total_views']}{_fmt_delta(kpis['delta_views'])}",
        f"- **J'aime cumulés :** {kpis['total_likes']}{_fmt_delta(kpis['delta_likes'])}",
        f"- **Commentaires cumulés :** {kpis['total_comments']}{_fmt_delta(kpis['delta_comments'])}",
        f"- **Moyenne / Médiane de vues :** {kpis['avg_views']} / {kpis['median_views']}",
        f"- **Vidéos à 0 vue :** {kpis['zero_view_count']}/{kpis['analyzed_videos_count']} ({int(round(kpis['zero_view_ratio'] * 100))}%)",
        f"- **Taux de J'aime / Commentaires :** {kpis['like_rate_pct']}% / {kpis['comment_rate_pct']}%",
        "",
        "## 🔎 Diagnostic (Pourquoi les vues et commentaires manquent)",
    ]

    for d in analysis.get("diagnostics") or []:
        lines.append(f"- **[{d['severity'].upper()}] {d['title']} :** {d['detail']}")

    lines.extend(["", "## 🎯 Plan d'action automatique & manuel (prochaines 24h)"])
    for idx, step in enumerate(analysis.get("action_plan") or [], start=1):
        lines.append(f"{idx}. {step}")

    recs = analysis.get("recommendations") or {}
    lines.extend([
        "",
        "## ⚙️ Réglages transmis automatiquement à Growth-Bot",
        f"- **Prochain appel à l'action (CTA) :** `{recs.get('recommended_cta', '')}`",
        f"- **Cadence recommandée :** {recs.get('recommended_clips_per_cycle', 3)} vidéos espacées par cycle",
        "- **Packs de hashtags chrétiens actifs :**",
        f"  - Prédication : `{' '.join(GrowthOptimizer.HASHTAG_PACKS['predication'])}`",
        f"  - Prière : `{' '.join(GrowthOptimizer.HASHTAG_PACKS['priere'])}`",
        f"  - Gospel : `{' '.join(GrowthOptimizer.HASHTAG_PACKS['gospel'])}`",
    ])

    top_videos = [v for v in (analysis.get("top_videos") or []) if int(v.get("views") or 0) > 0]
    if top_videos:
        lines.extend(["", "## 🏆 Meilleures vidéos actuelles"])
        for v in top_videos:
            lines.append(
                f"- **{v.get('title', 'Sans titre')[:70]}** — {v.get('views', 0)} vues | "
                f"{v.get('likes', 0)} j'aime | {v.get('comments', 0)} commentaires"
            )

    lines.append("")
    return "\n".join(lines)


class TikTokAccountAnalyzer:
    """Collecte les stats TikTok Studio en lecture seule et met à jour les fichiers d'intelligence."""

    def __init__(
        self,
        history_path: str = ANALYTICS_HISTORY_PATH,
        recommendations_path: str = RECOMMENDATIONS_PATH,
        report_path: str = HEALTH_REPORT_PATH,
        processed_videos_path: str = PROCESSED_VIDEOS_PATH,
        out_dir: str = "output/account_analyzer",
        session_id: Optional[str] = None,
    ):
        self.history_path = history_path
        self.recommendations_path = recommendations_path
        self.report_path = report_path
        self.processed_videos_path = processed_videos_path
        self.out_dir = out_dir
        self.session_id = session_id

    @staticmethod
    def _load_json(path: str, default: Any) -> Any:
        if not path or not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return default

    @staticmethod
    def _save_json(path: str, payload: Any) -> None:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _scrape_studio_rows(page, max_scrolls: int = 3) -> List[Dict[str, Any]]:
        """Collecte les lignes visibles de l'onglet Publications de TikTok Studio."""
        seen_keys = set()
        collected: List[Dict[str, Any]] = []

        js_extract = r"""() => {
            const thumbs = Array.from(document.querySelectorAll('img')).filter(img => {
                const r = img.getBoundingClientRect();
                return r.width > 35 && r.height > 55 && r.left > 200 && r.top > 120;
            });
            const rows = [];
            for (const img of thumbs) {
                let node = img.parentElement;
                let best = null;
                for (let depth = 0; depth < 8 && node; depth++) {
                    const r = node.getBoundingClientRect();
                    if (r.width > 700 && r.height >= 60 && r.height <= 220) {
                        best = node;
                        break;
                    }
                    node = node.parentElement;
                }
                if (best) {
                    const txt = (best.innerText || '').trim();
                    if (txt) rows.push(txt);
                }
            }
            return rows;
        }"""

        for scroll_idx in range(max_scrolls):
            try:
                raw_rows = page.evaluate(js_extract) or []
            except Exception:
                raw_rows = []

            for raw_text in raw_rows:
                parsed = parse_studio_row_text(raw_text)
                if not parsed:
                    continue
                key = (parsed["title"][:60], parsed["date"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    collected.append(parsed)

            if scroll_idx < max_scrolls - 1:
                try:
                    page.mouse.wheel(0, 900)
                    time.sleep(2)
                except Exception:
                    break

        return collected

    def collect_live_snapshot(self, max_scrolls: int = 3) -> Dict[str, Any]:
        """Ouvre TikTok Studio en lecture seule pour relever les stats actuelles du compte."""
        os.makedirs(self.out_dir, exist_ok=True)
        uploader = TikTokStudioUploader(session_id=self.session_id, screenshots_dir=self.out_dir)
        cookies, err = uploader._validate_and_prepare_cookies()
        if err:
            return {"status": "auth_error", "error": err.get("error", "Session TikTok indisponible.")}

        from playwright.sync_api import sync_playwright

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sync_playwright() as p:
            browser, context, page = uploader._launch_stealth_context(p, cookies)
            if not page:
                return {"status": "auth_error", "error": "Impossible d'initialiser la session Playwright."}
            try:
                uploader._warmup_session(page)
                page.goto(
                    "https://www.tiktok.com/tiktokstudio/content?lang=fr",
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                time.sleep(6)
                uploader._dismiss_popups(page)

                counts = uploader._read_studio_tab_counts(page)
                page.screenshot(
                    path=os.path.join(self.out_dir, "studio_snapshot.png"),
                    full_page=False,
                )
                videos = self._scrape_studio_rows(page, max_scrolls=max_scrolls)

                return {
                    "status": "ok",
                    "timestamp": timestamp,
                    "publications_count": counts.get("publications") if counts.get("publications") is not None else len(videos),
                    "drafts_count": counts.get("drafts") if counts.get("drafts") is not None else 0,
                    "videos": videos,
                }
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

    def run_analysis(self, snapshot: Optional[Dict[str, Any]] = None, max_scrolls: int = 3) -> Dict[str, Any]:
        """Exécute un cycle complet : collecte -> diagnostic -> sauvegarde historique & rapport."""
        live_snapshot = snapshot if snapshot is not None else self.collect_live_snapshot(max_scrolls=max_scrolls)
        if live_snapshot.get("status") != "ok":
            return live_snapshot

        history_data = self._load_json(self.history_path, {"snapshots": []})
        prev_snapshots = history_data.get("snapshots") if isinstance(history_data, dict) else []
        if not isinstance(prev_snapshots, list):
            prev_snapshots = []

        processed_data = self._load_json(self.processed_videos_path, {})
        processed_videos = processed_data.get("processed_videos", []) if isinstance(processed_data, dict) else []

        analysis = diagnose_account(
            live_snapshot,
            previous_snapshots=prev_snapshots,
            processed_videos=processed_videos,
        )

        timestamp = live_snapshot.get("timestamp") or datetime.datetime.now(datetime.timezone.utc).isoformat()
        snapshot_record = {
            "timestamp": timestamp,
            "status": analysis["status"],
            "kpis": analysis["kpis"],
            "active_alerts": analysis["recommendations"]["active_alerts"],
            "top_videos": analysis["top_videos"][:3],
        }
        prev_snapshots.append(snapshot_record)
        # Garder les 90 derniers relevés (~22 jours à raison de 4 relevés/jour)
        history_payload = {
            "last_updated": timestamp,
            "snapshots": prev_snapshots[-90:],
        }
        self._save_json(self.history_path, history_payload)
        self._save_json(self.recommendations_path, analysis["recommendations"])

        report_md = generate_health_report_markdown(analysis, timestamp)
        report_parent = os.path.dirname(self.report_path)
        if report_parent:
            os.makedirs(report_parent, exist_ok=True)
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        # Sauvegarde aussi dans output/ pour archivage artifact
        os.makedirs(self.out_dir, exist_ok=True)
        self._save_json(os.path.join(self.out_dir, "analysis_result.json"), {
            "snapshot": live_snapshot,
            "analysis": analysis,
        })

        # Notification optionnelle (Telegram / Webhook) si configurée
        try:
            notifier = TikTokNotifier()
            kpis = analysis["kpis"]
            alerts = ", ".join(analysis["recommendations"]["active_alerts"]) or "aucune"
            notifier.send_notification(
                title="📊 Analyse Compte TikTok 24/7",
                message=(
                    f"État : {analysis['status'].upper()} | "
                    f"Publications : {kpis['publications_count']} | "
                    f"Vues : {kpis['total_views']} | "
                    f"Commentaires : {kpis['total_comments']} | "
                    f"Alertes : {alerts}"
                ),
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "timestamp": timestamp,
            "analysis": analysis,
            "report_path": self.report_path,
            "recommendations_path": self.recommendations_path,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent d'analyse 24/7 du compte TikTok Studio")
    parser.add_argument("--out", default="output/account_analyzer", help="Dossier des captures et exports")
    parser.add_argument("--max-scrolls", type=int, default=3, help="Nombre de défilements de la liste Studio")
    args = parser.parse_args()

    analyzer = TikTokAccountAnalyzer(out_dir=args.out)
    result = analyzer.run_analysis(max_scrolls=args.max_scrolls)
    if result.get("status") != "ok":
        print(f"❌ [Account-Analyzer] Échec : {result.get('error', 'Erreur inconnue')}")
        raise SystemExit(1)

    kpis = result["analysis"]["kpis"]
    print(
        f"✅ [Account-Analyzer] Analyse terminée — "
        f"Publications: {kpis['publications_count']} | "
        f"Analysées: {kpis['analyzed_videos_count']} | "
        f"Vues: {kpis['total_views']} | "
        f"J'aime: {kpis['total_likes']} | "
        f"Commentaires: {kpis['total_comments']} | "
        f"État: {result['analysis']['status']}"
    )
    print(f"📄 Rapport mis à jour : {result['report_path']}")
    print(f"⚙️ Recommandations Growth-Bot : {result['recommendations_path']}")


if __name__ == "__main__":
    main()
