from types import SimpleNamespace

from src.planner import IssuePlan, Planner


def test_plan_extracts_paths_without_treating_commands_as_files():
    issue = SimpleNamespace(
        number=25,
        title="Create hello.py script",
        body=(
            "File must be at `src/hello.py`.\n"
            "Test with: `python src/hello.py`."
        ),
    )

    plan = Planner().build_issue_plan(issue)

    assert plan.allowed_paths == ["src/hello.py"]
    assert "python src/hello.py" not in plan.allowed_paths


def test_path_extraction_preserves_other_repo_paths_and_rejects_traversal():
    issue = SimpleNamespace(
        number=29,
        title="Update tool",
        body="Modify `openwebui/github_reader_tool.py` and not `../outside.py`.",
    )

    plan = Planner().build_issue_plan(issue)

    assert plan.allowed_paths == ["openwebui/github_reader_tool.py"]


def test_restored_plan_normalizes_legacy_command_path_entries():
    plan = IssuePlan.from_dict(
        {
            "issue_number": 25,
            "title": "Create hello.py script",
            "acceptance_criteria": [],
            "allowed_paths": ["python src/hello.py", "src/hello.py", "../outside.py"],
            "steps": [],
        }
    )

    assert plan.allowed_paths == ["src/hello.py"]
