from src.github_client import GitHubIssue
from src.planner import Planner


def _issue(title, body=""):
    return GitHubIssue(number=1, title=title, body=body, labels=[], state="open")


def test_bare_python_filename_defaults_to_src(tmp_path):
    plan = Planner().build_issue_plan(_issue("Create hello.py script"), tmp_path)
    assert plan.allowed_paths == ["src/hello.py"]


def test_bare_filename_prefers_unique_existing_file(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "tool.py").write_text("x")
    plan = Planner().build_issue_plan(_issue("Fix tool.py"), tmp_path)
    assert plan.allowed_paths == ["scripts/tool.py"]


def test_ambiguous_bare_filename_is_skipped(tmp_path):
    for d in ("a", "b"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "dup.py").write_text("x")
    plan = Planner().build_issue_plan(_issue("Fix dup.py"), tmp_path)
    assert plan.allowed_paths == []


def test_explicit_paths_take_precedence(tmp_path):
    plan = Planner().build_issue_plan(
        _issue("Update", "Edit `src/a.py` and hello.py"), tmp_path
    )
    assert plan.allowed_paths == ["src/a.py"]


def test_prose_without_filenames_has_empty_scope(tmp_path):
    plan = Planner().build_issue_plan(_issue("Melhorar a avaliacao"), tmp_path)
    assert plan.allowed_paths == []
