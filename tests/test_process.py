import os
import sys
import time
from pathlib import Path

import pytest

from src.process import run_bounded, sanitized_env
from src.tools import ToolHandler


def test_sanitized_env_removes_credentials(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-value-123")
    monkeypatch.setenv("CUSTOM_API_KEY", "another-secret")
    monkeypatch.setenv("HARMLESS", "yes")

    env = sanitized_env({"TMPDIR": "/x"})

    assert "GITHUB_TOKEN" not in env
    assert "CUSTOM_API_KEY" not in env
    assert env["HARMLESS"] == "yes"
    assert env["TMPDIR"] == "/x"


def test_run_bounded_returns_output(tmp_path: Path):
    result = run_bounded(
        [sys.executable, "-c", "print('hi')"], str(tmp_path), timeout=20
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "hi"
    assert not result.timed_out


def test_run_bounded_kills_child_processes_on_timeout(tmp_path: Path):
    marker = tmp_path / "grandchild.txt"
    code = (
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c', "
        "\"import sys, time; time.sleep(4); open(sys.argv[1], 'w').write('alive')\", "
        "sys.argv[1]])\n"
        "time.sleep(30)\n"
    )

    started = time.monotonic()
    result = run_bounded(
        [sys.executable, "-c", code, str(marker)], str(tmp_path), timeout=1
    )
    time.sleep(5)

    assert result.timed_out
    assert time.monotonic() - started < 20
    assert not marker.exists()


def test_tool_handler_hides_secrets_from_commands(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-value-123")
    handler = ToolHandler(str(tmp_path))

    output = handler.run_command(
        "python -c \"import os; print(os.environ.get('GITHUB_TOKEN', 'absent'))\""
    )
    handler.cleanup()

    assert output.strip() == "absent"


def test_tool_handler_uses_and_removes_task_temp_dir(tmp_path: Path):
    handler = ToolHandler(str(tmp_path))

    output = handler.run_command(
        "python -c \"import tempfile; print(tempfile.gettempdir())\""
    ).strip()
    temp_dir = Path(output)

    assert temp_dir.name.startswith("bastiao-")
    assert temp_dir.is_dir()
    handler.cleanup()
    assert not temp_dir.exists()
    handler.cleanup()


@pytest.mark.skipif(sys.platform == "win32", reason="rlimits are POSIX-only")
def test_memory_limit_is_enforced(tmp_path: Path):
    result = run_bounded(
        [sys.executable, "-c", "x = bytearray(512 * 1024 * 1024)"],
        str(tmp_path),
        timeout=20,
        memory_mb=128,
    )

    assert result.returncode != 0
    assert "MemoryError" in result.stderr
