import os
import sys
import json
import yaml
import tempfile
import subprocess
from pathlib import Path
import pytest

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PYTHON_EXEC = sys.executable


# =====================================================================
# 1. Stress Tests: CLI Argument Parsing & Validation (main.py)
# =====================================================================

def test_cli_empty_inputs_exit_code_1():
    """Vérifie que main.py sort proprement avec le code 1 et affiche l'aide si aucun argument ou chaîne vide."""
    cases = [
        [PYTHON_EXEC, "main.py"],
        [PYTHON_EXEC, "main.py", "--url", ""],
        [PYTHON_EXEC, "main.py", "--video", ""],
        [PYTHON_EXEC, "main.py", "--batch", ""],
    ]
    for cmd in cases:
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        assert res.returncode == 1, f"Échec pour commande {cmd}: code={res.returncode}, stderr={res.stderr}"
        assert "Astuce Karl" in res.stdout or "usage:" in res.stdout or "usage:" in res.stderr


def test_cli_invalid_choices_and_types_exit_code_2():
    """Vérifie qu'argparse rejette les options invalides avec le code d'erreur 2."""
    cases = [
        [PYTHON_EXEC, "main.py", "--theme", "gothique"],
        [PYTHON_EXEC, "main.py", "--publish", "secret_mode"],
        [PYTHON_EXEC, "main.py", "--clips", "invalid_number"],
    ]
    for cmd in cases:
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        assert res.returncode == 2, f"Échec pour commande {cmd}: code={res.returncode}"
        assert "invalid choice" in res.stderr or "invalid int value" in res.stderr


def test_cli_batch_file_nonexistent_and_comment_filtering():
    """Vérifie la robustesse de l'option --batch (fichier inexistant vs filtrage commentaires)."""
    # 1. Fichier inexistant -> code 1
    res = subprocess.run(
        [PYTHON_EXEC, "main.py", "--batch", "fichier_qui_n_existe_pas_9999.txt"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True
    )
    assert res.returncode == 1
    assert "Fichier batch introuvable" in res.stdout or "Fichier batch introuvable" in res.stderr

    # 2. Fichier batch valide avec commentaires et lignes vides
    with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
        f.write("# Commentaire d'introduction\n")
        f.write("\n")
        f.write("https://youtu.be/test1\n")
        f.write("   \n")
        f.write("# Autre commentaire\n")
        f.write("https://youtu.be/test2\n")
        batch_path = f.name

    try:
        from unittest.mock import patch, MagicMock
        import main
        with patch("sys.argv", ["main.py", "--batch", batch_path]):
            with patch("main.TikTokPipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_pipeline_cls.return_value = mock_inst
                main.main()
                mock_inst.process_batch.assert_called_once_with(
                    ["https://youtu.be/test1", "https://youtu.be/test2"],
                    top_k=1
                )
    finally:
        if os.path.exists(batch_path):
            os.remove(batch_path)


def test_cli_weird_characters_and_emojis():
    """Vérifie la préservation fidèle des caractères spéciaux, guillemets et emojis dans la CLI."""
    from unittest.mock import patch, MagicMock
    import main

    hostile_watermark = "Karl's \"Studio\" & 🕊️ Gospel 🔥 ($100) ; <test>"
    hostile_url = "https://youtube.com/watch?v=sample&param=1;rm -rf /;$(whoami)"

    with patch("sys.argv", ["main.py", "--url", hostile_url, "--watermark", hostile_watermark, "--publish", "none"]):
        with patch("main.TikTokPipeline") as mock_pipeline_cls:
            mock_inst = MagicMock()
            mock_pipeline_cls.return_value = mock_inst
            main.main()

            mock_pipeline_cls.assert_called_once_with(
                output_dir="output",
                theme_name="gospel",
                watermark=hostile_watermark,
                with_progress_bar=True,
                webhook_url=None,
                publish_mode="none"
            )
            mock_inst.process_url.assert_called_once_with(hostile_url, top_k=1)


# =====================================================================
# 2. Workflow YAML Syntax & Structure Verification
# =====================================================================

def test_workflow_generate_tiktok_yaml_validity():
    """Vérifie la syntaxe YAML et la structure des inputs et jobs de generate_tiktok.yml."""
    yaml_path = PROJECT_ROOT / ".github" / "workflows" / "generate_tiktok.yml"
    assert yaml_path.exists(), f"Workflow introuvable: {yaml_path}"

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict)
    assert "name" in data
    # In YAML 1.1 'on' is parsed as True or string 'on'
    on_key = True if True in data else "on"
    assert on_key in data

    workflow_dispatch = data[on_key].get("workflow_dispatch")
    assert workflow_dispatch is not None
    inputs = workflow_dispatch.get("inputs", {})

    expected_inputs = ["video_url", "clips_count", "theme", "watermark", "publish_mode", "progress_bar"]
    for inp in expected_inputs:
        assert inp in inputs, f"Input manquant dans workflow_dispatch: {inp}"

    # Vérification des options autorisées
    assert set(inputs["theme"]["options"]) == {"gospel", "gold", "neon", "minimal"}
    assert set(inputs["publish_mode"]["options"]) == {"draft", "public", "none"}
    assert set(inputs["clips_count"]["options"]) == {"1", "2", "3"}

    # Vérification des jobs
    jobs = data.get("jobs", {})
    assert "build-tiktok" in jobs
    steps = jobs["build-tiktok"].get("steps", [])
    step_names = [s.get("name", "") for s in steps]
    assert any("Lancement de la Machine" in n for n in step_names)
    assert any("Archivage" in n for n in step_names)


def test_workflow_ci_yaml_validity():
    """Vérifie la syntaxe YAML et la structure du workflow CI."""
    yaml_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    assert yaml_path.exists(), f"Workflow introuvable: {yaml_path}"

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict)
    assert "name" in data
    on_key = True if True in data else "on"
    assert on_key in data

    jobs = data.get("jobs", {})
    assert "test" in jobs
    steps = jobs["test"].get("steps", [])
    step_runs = [s.get("run", "") for s in steps]
    assert any("pytest -v" in r for r in step_runs)


# =====================================================================
# 3. Bash Array Execution Stress Simulation
# =====================================================================

def test_workflow_bash_array_injection_safety():
    """Simule l'exécution de la boucle bash de GitHub Actions avec des arguments d'injection hostile."""
    bash_script = """
    set -eo pipefail

    cmd=(python -c 'import sys, json; print(json.dumps(sys.argv[1:]))' --url "$VIDEO_URL" --clips "$CLIPS_COUNT" --theme "$THEME" --watermark "$WATERMARK" --publish "$PUBLISH_MODE" --output output)
    if [ "$PROGRESS_BAR" != "true" ]; then
      cmd+=(--no-progress-bar)
    fi
    if [ -n "$TIKTOK_WEBHOOK_URL" ]; then
      cmd+=(--webhook "$TIKTOK_WEBHOOK_URL")
    fi
    "${cmd[@]}"
    """

    env_sim = os.environ.copy()
    env_sim["VIDEO_URL"] = "https://youtube.com/watch?v=sample&id=1; rm -rf /; $(whoami); `uname -a`"
    env_sim["CLIPS_COUNT"] = "2"
    env_sim["THEME"] = "neon"
    env_sim["WATERMARK"] = "Karl's \"Studio\" & <Gospel> $HOME 🕊️"
    env_sim["PUBLISH_MODE"] = "draft"
    env_sim["PROGRESS_BAR"] = "false"
    env_sim["TIKTOK_WEBHOOK_URL"] = "https://discord.com/api/webhooks/karl?token=123&test=1"

    proc = subprocess.run(["bash", "-c", bash_script], env=env_sim, capture_output=True, text=True)
    assert proc.returncode == 0, f"Erreur script bash: {proc.stderr}"

    received_args = json.loads(proc.stdout.strip())

    # Vérification anti-injection : aucune sous-commande $(...) ou `...` n'a été exécutée
    assert "--url" in received_args
    url_idx = received_args.index("--url") + 1
    assert received_args[url_idx] == env_sim["VIDEO_URL"]

    assert "--watermark" in received_args
    wm_idx = received_args.index("--watermark") + 1
    assert received_args[wm_idx] == env_sim["WATERMARK"]

    assert "--no-progress-bar" in received_args
    assert "--webhook" in received_args
    webhook_idx = received_args.index("--webhook") + 1
    assert received_args[webhook_idx] == env_sim["TIKTOK_WEBHOOK_URL"]


# =====================================================================
# 4. Output Directory Idempotency & Clean Payload Generation
# =====================================================================

def test_pipeline_results_json_schema():
    """Vérifie le format et l'idempotence de tiktok_results.json après exécution."""
    results_file = PROJECT_ROOT / "output" / "tiktok_results.json"
    if results_file.exists():
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "source_title" in data
        assert "clips_count" in data
        assert "theme" in data
        assert "watermark" in data
        assert "clips" in data
        assert isinstance(data["clips"], list)
        if data["clips"]:
            clip = data["clips"][0]
            assert "video_path" in clip
            assert "sheet_path" in clip
            assert "hook" in clip
            assert "retention" in clip
            assert "publication" in clip
