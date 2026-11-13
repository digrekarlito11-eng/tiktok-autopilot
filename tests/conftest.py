"""
conftest.py - Pytest fixtures and environment configuration for tiktok-autopilot.
Provides isolated temporary directories, synthetic video generation, VTT samples,
and mock helpers for offline, deterministic testing.
"""

import os
import sys
import subprocess
import pytest
from typing import Dict, Any, List

# Ensure repository root is on sys.path for direct imports from src
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

@pytest.fixture(autouse=True)
def clean_test_env(monkeypatch):
    """
    Ensures tests run in a clean environment without leaking external tokens
    or webhook URLs unless explicitly set in specific tests.
    """
    monkeypatch.delenv("TIKTOK_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("TIKTOK_WEBHOOK_URL", raising=False)

@pytest.fixture
def test_output_dir(tmp_path):
    """Provides a fresh isolated directory for output artifacts."""
    out_dir = tmp_path / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir)

@pytest.fixture
def test_temp_dir(tmp_path):
    """Provides a fresh isolated directory for downloads/temporary files."""
    tmp = tmp_path / "downloads"
    tmp.mkdir(parents=True, exist_ok=True)
    return str(tmp)

@pytest.fixture
def sample_preaching_segments() -> List[Dict[str, Any]]:
    """
    Sample transcript segments from a typical Christian preaching session
    containing prophetic cues, faith declarations, and spiritual combat keywords.
    """
    return [
        {
            "start": 0.0,
            "end": 4.5,
            "text": "Écoutez ce message prophétique que Dieu m'a révélé."
        },
        {
            "start": 4.5,
            "end": 10.0,
            "text": "Une saison de combat spirituel difficile se termine pour toi."
        },
        {
            "start": 10.0,
            "end": 18.5,
            "text": "Le Seigneur annonce qu'un grand miracle se prépare dans ta vie."
        },
        {
            "start": 18.5,
            "end": 26.0,
            "text": "Ne doute plus de ta foi car ta victoire est proche."
        },
        {
            "start": 26.0,
            "end": 33.0,
            "text": "Reçois cette bénédiction divine et déclare ta grâce aujourd'hui."
        }
    ]

@pytest.fixture
def sample_vtt_file(tmp_path) -> str:
    """Generates a standard WebVTT file with clean preaching cues."""
    vtt_path = tmp_path / "preaching_sample.vtt"
    content = """WEBVTT

00:00:00.000 --> 00:00:04.500
Écoutez ce message prophétique que Dieu m'a révélé.

00:00:04.500 --> 00:00:10.000
Une saison de combat spirituel difficile se termine pour toi.

00:00:10.000 --> 00:00:18.500
Le Seigneur annonce qu'un grand miracle se prépare dans ta vie.

00:00:18.500 --> 00:00:26.000
Ne doute plus de ta foi car ta victoire est proche.

00:00:26.000 --> 00:00:33.000
Reçois cette bénédiction divine et déclare ta grâce aujourd'hui.
"""
    vtt_path.write_text(content, encoding="utf-8")
    return str(vtt_path)

@pytest.fixture
def rolling_vtt_file(tmp_path) -> str:
    """
    Generates a YouTube auto-generated rolling WebVTT file where cues
    overlap and repeat progressive text windows.
    """
    vtt_path = tmp_path / "rolling_youtube.vtt"
    content = """WEBVTT

00:00:01.000 --> 00:00:03.500
Dieu va faire un miracle

00:00:03.500 --> 00:00:06.000
Dieu va faire un miracle dans ta vie reçois

00:00:06.000 --> 00:00:09.000
dans ta vie reçois cette bénédiction aujourd'hui
"""
    vtt_path.write_text(content, encoding="utf-8")
    return str(vtt_path)

@pytest.fixture(scope="session")
def synthetic_preaching_video(tmp_path_factory) -> str:
    """
    Generates a fast 5-second synthetic MP4 video (1280x720, 30fps with sine audio)
    using FFmpeg lavfi filters. Reusable across tests for rendering verification.
    """
    session_dir = tmp_path_factory.mktemp("video_fixture")
    video_path = session_dir / "synthetic_preach_source.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        str(video_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return str(video_path)
