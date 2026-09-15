import json
from pathlib import Path
from unittest.mock import patch

from src.quality_gate import QualityGate


def test_quality_gate_runs_tests_compileall_and_diff_check(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "module.py").write_text("VALUE = 1\n")

    commands = QualityGate(tmp_path)._commands()

    assert [name for name, _ in commands] == ["pytest", "compileall", "git-diff-check"]


def test_quality_gate_discovers_defined_package_scripts(tmp_path: Path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"lint": "eslint .", "typecheck": "tsc --noEmit"}})
    )

    names = [name for name, _ in QualityGate(tmp_path)._commands()]

    assert names == ["npm:lint", "npm:typecheck", "git-diff-check"]


def test_quality_gate_reports_command_failure(tmp_path: Path):
    gate = QualityGate(tmp_path)

    with patch("src.quality_gate.subprocess.run") as run:
        run.return_value.returncode = 1
        run.return_value.stdout = "failure"
        run.return_value.stderr = ""

        result = gate.run()

    assert not result.passed
    assert result.checks[-1].name == "git-diff-check"
    assert result.checks[-1].output == "failure"
    assert result.failure_summary() == "git-diff-check: exit 1"


def test_quality_gate_reports_timeout(tmp_path: Path):
    gate = QualityGate(tmp_path)

    with patch(
        "src.quality_gate.subprocess.run",
        side_effect=__import__("subprocess").TimeoutExpired(["git"], 1, output="slow"),
    ):
        result = gate.run()

    assert not result.passed
    assert result.checks[-1].timed_out
    assert result.failure_summary() == "git-diff-check: timeout"
