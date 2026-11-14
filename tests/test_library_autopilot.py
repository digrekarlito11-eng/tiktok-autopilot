import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.library_autopilot import LibraryAutopilot, DEFAULT_PLAYLIST_URL

def test_library_autopilot_init(tmp_path):
    history_file = str(tmp_path / "history.json")
    report_file = str(tmp_path / "REPORT.md")

    bot = LibraryAutopilot(
        playlist_url="https://youtube.com/playlist?list=TEST123",
        history_path=history_file,
        report_path=report_file,
        theme="gospel",
        clips_count=10
    )

    assert bot.playlist_url == "https://youtube.com/playlist?list=TEST123"
    assert bot.clips_count == 10
    assert bot.history_data["total_processed"] == 0
    assert bot.history_data["processed_video_ids"] == []

def test_get_unprocessed_videos_filtering(tmp_path):
    history_file = str(tmp_path / "history.json")
    report_file = str(tmp_path / "REPORT.md")

    initial_history = {
        "playlist_url": "https://youtube.com/playlist?list=TEST123",
        "total_processed": 1,
        "processed_video_ids": ["vid_1"],
        "history": [{"id": "vid_1", "title": "Vidéo 1"}]
    }
    with open(history_file, "w") as f:
        json.dump(initial_history, f)

    bot = LibraryAutopilot(
        playlist_url="https://youtube.com/playlist?list=TEST123",
        history_path=history_file,
        report_path=report_file
    )

    mock_items = [
        {"id": "vid_1", "title": "Vidéo 1", "duration": 1800, "url": "https://yt.com/vid_1"},
        {"id": "vid_2", "title": "Vidéo 2", "duration": 1500, "url": "https://yt.com/vid_2"}
    ]

    with patch.object(bot, "fetch_playlist_items", return_value=mock_items):
        unprocessed = bot.get_unprocessed_videos()
        assert len(unprocessed) == 1
        assert unprocessed[0]["id"] == "vid_2"

def test_dry_run_cycle(tmp_path):
    history_file = str(tmp_path / "history.json")
    report_file = str(tmp_path / "REPORT.md")

    bot = LibraryAutopilot(
        playlist_url="https://youtube.com/playlist?list=TEST123",
        history_path=history_file,
        report_path=report_file
    )

    mock_items = [
        {"id": "vid_3", "title": "Prédication Puissante", "duration": 2000, "url": "https://yt.com/vid_3"}
    ]

    with patch.object(bot, "fetch_playlist_items", return_value=mock_items):
        res = bot.run_cycle(dry_run=True)
        assert res["status"] == "dry_run"
        assert res["selected_video"]["id"] == "vid_3"

def test_generate_markdown_report(tmp_path):
    history_file = str(tmp_path / "history.json")
    report_file = str(tmp_path / "REPORT.md")

    bot = LibraryAutopilot(
        history_path=history_file,
        report_path=report_file
    )

    sample_video = {
        "id": "abc123",
        "title": "La Guérison de l'Âme - Ps Juliana Ondo",
        "url": "https://youtube.com/watch?v=abc123",
        "duration_string": "1:20:00"
    }
    sample_clips = [
        {
            "clip_number": 1,
            "duration": 75.0,
            "hook": "DIEU A VU TES LARMES CACHÉES",
            "retention": "88%",
            "publication": {"status": "success"}
        }
    ]

    bot.generate_markdown_report(status="SUCCES", last_video=sample_video, clips_info=sample_clips)

    assert os.path.exists(report_file)
    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "La Guérison de l'Âme - Ps Juliana Ondo" in content
    assert "DIEU A VU TES LARMES CACHÉES" in content
    assert "Brouillons TikTok Studio" in content


def test_run_cycle_does_not_mark_processed_on_auth_error(tmp_path):
    history_file = str(tmp_path / "history.json")
    report_file = str(tmp_path / "REPORT.md")

    bot = LibraryAutopilot(
        history_path=history_file,
        report_path=report_file,
        publish_mode="draft",
        clips_count=2,
    )

    mock_items = [
        {"id": "vid_retry", "title": "Prédication Test", "duration": 1800, "url": "https://yt.com/vid_retry"}
    ]
    fake_pipeline_result = {
        "clips": [
            {"clip_number": 1, "duration": 90.0, "hook": "HOOK 1", "retention": "90%", "publication": {"status": "auth_error"}},
            {"clip_number": 2, "duration": 95.0, "hook": "HOOK 2", "retention": "88%", "publication": {"status": "auth_error"}},
        ]
    }

    with patch.object(bot, "fetch_playlist_items", return_value=mock_items):
        with patch("src.library_autopilot.TikTokPipeline") as mock_pipe_cls:
            mock_pipe_cls.return_value.process_url.return_value = fake_pipeline_result
            res = bot.run_cycle()

    assert res["status"] == "auth_error"
    assert res["clips_generated"] == 2
    assert res["clips_published"] == 0
    assert bot.history_data["processed_video_ids"] == []
    assert bot.history_data["total_processed"] == 0

    with open(report_file, "r", encoding="utf-8") as f:
        report = f.read()
    assert "EN_ATTENTE_SESSION" in report
    assert "Liste des 2 Shorts" in report
    assert "Liste des 10 Shorts" not in report


def test_run_cycle_marks_processed_on_success(tmp_path):
    history_file = str(tmp_path / "history.json")
    report_file = str(tmp_path / "REPORT.md")

    bot = LibraryAutopilot(
        history_path=history_file,
        report_path=report_file,
        publish_mode="draft",
        clips_count=2,
    )

    mock_items = [
        {"id": "vid_ok", "title": "Prédication Validée", "duration": 1800, "url": "https://yt.com/vid_ok"}
    ]
    fake_pipeline_result = {
        "clips": [
            {"clip_number": 1, "duration": 90.0, "hook": "HOOK 1", "retention": "90%", "publication": {"status": "success"}},
            {"clip_number": 2, "duration": 95.0, "hook": "HOOK 2", "retention": "88%", "publication": {"status": "success"}},
        ]
    }

    with patch.object(bot, "fetch_playlist_items", return_value=mock_items):
        with patch("src.library_autopilot.TikTokPipeline") as mock_pipe_cls:
            mock_pipe_cls.return_value.process_url.return_value = fake_pipeline_result
            res = bot.run_cycle()

    assert res["status"] == "success"
    assert res["clips_published"] == 2
    assert bot.history_data["processed_video_ids"] == ["vid_ok"]
    assert bot.history_data["total_processed"] == 1

    with open(report_file, "r", encoding="utf-8") as f:
        report = f.read()
    assert "SUCCES" in report
    assert "Liste des 2 Shorts" in report

