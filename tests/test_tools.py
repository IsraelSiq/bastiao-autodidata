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
