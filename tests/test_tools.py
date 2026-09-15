from pathlib import Path

from src.tools import ToolHandler


def test_tool_handler_rejects_path_traversal(tmp_path: Path):
    handler = ToolHandler(str(tmp_path))
    assert "escapes repository root" in handler.read_file("../outside.txt")
    absolute = str(Path(tmp_path.anchor) / "outside.txt")
    assert "absolute paths are not allowed" in handler.write_file(f"{absolute} value")


def test_tool_handler_rejects_unapproved_commands(tmp_path: Path):
    handler = ToolHandler(str(tmp_path))
    assert "Command not allowed" in handler.run_command("sh -c 'echo unsafe'")


def test_tool_handler_rejects_mutating_git_commands(tmp_path: Path):
    handler = ToolHandler(str(tmp_path))
    assert "Git action not allowed" in handler.run_command("git init")
    assert "Git action not allowed" in handler.run_command("git push origin main")


def test_tool_handler_rejects_reading_directories(tmp_path: Path):
    handler = ToolHandler(str(tmp_path))
    (tmp_path / "src").mkdir()
    assert "Not a file" in handler.read_file("src")


def test_tool_handler_rejects_package_installation(tmp_path: Path):
    handler = ToolHandler(str(tmp_path))
    assert "Package installation is not allowed" in handler.run_command("python -m pip install astroid")
    assert "Package installation is not allowed" in handler.run_command("npm install requests")


def test_tool_handler_enforces_planner_scope(tmp_path: Path):
    handler = ToolHandler(str(tmp_path), allowed_paths=["src/allowed.py"])

    assert "Path is outside the planner scope" in handler.write_file(
        "src/other.py value"
    )
    assert handler.write_file("src/allowed.py value") == "OK: Wrote src/allowed.py"


def test_tool_handler_disables_writes_when_strict_scope_is_empty(tmp_path: Path):
    handler = ToolHandler(str(tmp_path), strict_scope=True)

    assert "Planner scope is empty" in handler.write_file("src/blocked.py value")


def test_tool_handler_enforces_command_count_and_output_limits(tmp_path: Path):
    handler = ToolHandler(
        str(tmp_path),
        max_commands=1,
        max_output_chars=5,
    )

    assert "truncated at 5" in handler.run_command("python -c \"print('123456789')\"")
    assert "command limit reached" in handler.run_command("python -c \"print('ok')\"")


def test_tool_handler_enforces_write_size_limit(tmp_path: Path):
    handler = ToolHandler(str(tmp_path), max_write_bytes=3)

    assert "exceeds limit" in handler.write_file("src/file.py abcd")


def test_tool_handler_reports_configured_timeout(tmp_path: Path):
    handler = ToolHandler(str(tmp_path), command_timeout_seconds=1)

    assert "Timeout (1s)" in handler.run_command("python -c \"import time; time.sleep(2)\"")


def test_tool_handler_accepts_completion_action(tmp_path: Path):
    assert ToolHandler(str(tmp_path)).execute("complete") == "OK: Completion requested"
