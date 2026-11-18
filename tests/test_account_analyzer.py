"""Tests unitaires pour l'agent d'analyse de compte TikTok 24/7 (src/account_analyzer.py)."""

import json
import os
import tempfile

from src.account_analyzer import (
    COMMENT_MAGNET_ROTATION,
    TikTokAccountAnalyzer,
    diagnose_account,
    generate_health_report_markdown,
    parse_duration_seconds,
    parse_metric_number,
    parse_studio_row_text,
)
from src.growth_optimizer import GrowthOptimizer


class TestMetricAndRowParsing:
    def test_parse_metric_number_formats(self):
        assert parse_metric_number("0") == 0
        assert parse_metric_number("42") == 42
        assert parse_metric_number("1 250") == 1250
        assert parse_metric_number("1,2K") == 1200
        assert parse_metric_number("3.5M") == 3_500_000
        assert parse_metric_number("-") == 0
        assert parse_metric_number(None) == 0

    def test_parse_duration_seconds(self):
        assert parse_duration_seconds("01:59") == 119
        assert parse_duration_seconds("00:45") == 45
        assert parse_duration_seconds("1:02:03") == 3723
        assert parse_duration_seconds("invalid") is None

    def test_parse_studio_row_text_french_ui(self):
        raw = (
            "01:59\n"
            "📖 Dieu alléluia en être en harmonie au niveau spirituel...\n"
            "15 nov., 13:48\n"
            "Tout le monde\n"
            "1,2K\n"
            "85\n"
            "14\n"
        )
        row = parse_studio_row_text(raw)
        assert row is not None
        assert row["duration"] == "01:59"
        assert row["duration_seconds"] == 119
        assert "harmonie" in row["title"]
        assert row["date"] == "15 nov., 13:48"
        assert "Tout le monde" in row["privacy"]
        assert row["views"] == 1200
        assert row["likes"] == 85
        assert row["comments"] == 14


class TestAccountDiagnostics:
    def test_diagnose_zero_views_burst_and_long_clips(self):
        snapshot = {
            "timestamp": "2026-11-18T12:00:00+00:00",
            "publications_count": 32,
            "drafts_count": 0,
            "videos": [
                {"title": f"Clip {i}", "date": f"15 nov., 13:{30 + i * 2:02d}", "duration_seconds": 118, "privacy": "Tout le monde", "views": 0, "likes": 0, "comments": 0}
                for i in range(6)
            ],
        }
        processed = [
            {
                "clips_published": 10,
                "clips_summary": [{"hook": "LA VÉRITÉ SUR LE MARIAGE ⚡"} for _ in range(8)]
                + [{"hook": "AUTRE HOOK"} for _ in range(2)],
            }
        ]

        result = diagnose_account(snapshot, previous_snapshots=[], processed_videos=processed)
        codes = {d["code"] for d in result["diagnostics"]}

        assert result["status"] == "critique"
        assert "burst_posting" in codes
        assert "zero_views_wall" in codes
        assert "long_clips_retention" in codes
        assert "low_comments" in codes
        assert "repetitive_hooks" in codes
        assert result["recommendations"]["recommended_clips_per_cycle"] == 3
        assert result["recommendations"]["recommended_cta"] == COMMENT_MAGNET_ROTATION[0]

    def test_diagnose_healthy_account_and_deltas(self):
        snapshot = {
            "timestamp": "2026-11-18T18:00:00+00:00",
            "publications_count": 10,
            "drafts_count": 0,
            "videos": [
                {"title": "Parole 1", "date": "18 nov., 06:00", "duration_seconds": 58, "privacy": "Tout le monde", "views": 1500, "likes": 180, "comments": 35},
                {"title": "Parole 2", "date": "18 nov., 13:00", "duration_seconds": 62, "privacy": "Tout le monde", "views": 900, "likes": 95, "comments": 20},
                {"title": "Parole 3", "date": "18 nov., 19:00", "duration_seconds": 55, "privacy": "Tout le monde", "views": 600, "likes": 70, "comments": 12},
            ],
        }
        prev = [{"kpis": {"total_views": 2000, "total_likes": 200, "total_comments": 40}}]

        result = diagnose_account(snapshot, previous_snapshots=prev, processed_videos=[])
        assert result["status"] == "sain"
        assert result["kpis"]["total_views"] == 3000
        assert result["kpis"]["delta_views"] == 1000
        assert result["kpis"]["delta_comments"] == 27
        assert result["recommendations"]["recommended_cta"] == COMMENT_MAGNET_ROTATION[1]

        md = generate_health_report_markdown(result, snapshot["timestamp"])
        assert "3000 (+1000)" in md
        assert "#Predication" in md
        assert "#PriereDuJour" in md
        assert "#GospelAfricain" in md


class TestAnalyzerPersistenceAndGrowthLoop:
    def test_run_analysis_writes_history_report_and_feeds_growth_optimizer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = os.path.join(tmpdir, "account_analytics.json")
            recs_path = os.path.join(tmpdir, "growth_recommendations.json")
            report_path = os.path.join(tmpdir, "ACCOUNT_HEALTH_REPORT.md")
            out_dir = os.path.join(tmpdir, "out")

            analyzer = TikTokAccountAnalyzer(
                history_path=history_path,
                recommendations_path=recs_path,
                report_path=report_path,
                processed_videos_path=os.path.join(tmpdir, "missing.json"),
                out_dir=out_dir,
            )

            fake_snapshot = {
                "status": "ok",
                "timestamp": "2026-11-18T18:00:00+00:00",
                "publications_count": 32,
                "drafts_count": 0,
                "videos": [
                    {"title": "Clip A", "date": "18 nov., 12:00", "duration_seconds": 115, "privacy": "Tout le monde", "views": 0, "likes": 0, "comments": 0},
                    {"title": "Clip B", "date": "18 nov., 12:02", "duration_seconds": 118, "privacy": "Moi uniquement", "views": 0, "likes": 0, "comments": 0},
                    {"title": "Clip C", "date": "18 nov., 12:05", "duration_seconds": 119, "privacy": "Tout le monde", "views": 0, "likes": 0, "comments": 0},
                    {"title": "Clip D", "date": "18 nov., 12:08", "duration_seconds": 117, "privacy": "Tout le monde", "views": 0, "likes": 0, "comments": 0},
                ],
            }

            res = analyzer.run_analysis(snapshot=fake_snapshot)
            assert res["status"] == "ok"
            assert os.path.exists(history_path)
            assert os.path.exists(recs_path)
            assert os.path.exists(report_path)

            with open(recs_path, "r", encoding="utf-8") as f:
                recs = json.load(f)
            assert "burst_posting" in recs["active_alerts"]
            assert "privacy_or_review_hold" in recs["active_alerts"]

            # Vérifie que GrowthOptimizer charge bien le CTA recommandé par l'agent d'analyse
            growth = GrowthOptimizer(recommendations_path=recs_path)
            pkg = growth.generate_growth_package({"text": "Un message d'évangile sur la foi."}, "Prédication")
            assert pkg["cta"] == recs["recommended_cta"]
            assert pkg["hashtags"] == GrowthOptimizer.HASHTAG_PACKS["predication"]
