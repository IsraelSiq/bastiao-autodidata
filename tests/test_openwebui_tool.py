import importlib.util
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "github_reader_tool", Path(__file__).parent.parent / "openwebui" / "github_reader_tool.py"
)
tool_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool_mod)


def test_parse_urls():
    info = tool_mod.parse_github_url("veja https://github.com/IsraelSiq/bastiao-autodidata/issues/37")
    assert info["kind"] == "issues" and info["rest"] == "37"
    blob = tool_mod.parse_github_url("https://github.com/a/b/blob/main/docs/x.md")
    assert blob["rest"] == "main/docs/x.md"


def test_repo_not_allowed_blocks_request():
    tools = tool_mod.Tools()
    with patch.object(tool_mod.requests, "get") as get:
        result = tools.get_issue(1, "evil/repo")
    assert "nao permitido" in result
    get.assert_not_called()


def test_list_issues_skips_prs():
    tools = tool_mod.Tools()
    items = [
        {"number": 1, "state": "open", "title": "A"},
        {"number": 2, "state": "open", "title": "B", "pull_request": {}},
    ]
    with patch.object(tools, "_get", return_value=items):
        out = tools.list_issues()
    assert "#1" in out and "#2" not in out


def test_read_link_routes_blob_and_truncates():
    tools = tool_mod.Tools()
    tools.valves.max_chars = 10
    calls = []

    def fake_get(path, raw=False):
        calls.append(path)
        return {"type": "file"} if not raw else "x" * 50

    with patch.object(tools, "_get", side_effect=fake_get):
        out = tools.read_github_link("https://github.com/IsraelSiq/bastiao-autodidata/blob/main/ROADMAP.md")
    assert out.endswith("[truncado]")
    assert "contents/ROADMAP.md?ref=main" in calls[0]
