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
