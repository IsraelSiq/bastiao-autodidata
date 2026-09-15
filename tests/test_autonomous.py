from unittest.mock import Mock
import requests
from src.metrics import CycleMetrics

from src.autonomous import AutonomousRunner


def test_issue_scope_rejects_unrelated_file():
    runner = AutonomousRunner.__new__(AutonomousRunner)
    files = [{"path": "src/__main__.py", "content": "import logging_config"}]

    assert not runner._has_in_scope_diff(
        "Create hello.py script",
        "File must be at `src/hello.py`.",
        files,
    )


def test_issue_scope_accepts_explicit_target_file():
    runner = AutonomousRunner.__new__(AutonomousRunner)
    files = [{"path": "src/hello.py", "content": "print('Hello from Bastiao!')\n"}]

    assert runner._has_in_scope_diff(
        "Create hello.py script",
        "File must be at `src/hello.py`.",
        files,
    )


def test_issue_scope_allows_issues_without_explicit_paths(tmp_path):
    runner = AutonomousRunner.__new__(AutonomousRunner)
    runner.workspace = tmp_path
    files = [{"path": "src/planner.py", "content": "def plan():\n    pass\n"}]

    assert runner._has_in_scope_diff("Improve planner", "Refactor the planner.", files)


def test_issue_scope_rejects_unmentioned_existing_file(tmp_path):
    runner = AutonomousRunner.__new__(AutonomousRunner)
    runner.workspace = tmp_path
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "logging_config.py").write_text("import logging\n")
    files = [{"path": "src/logging_config.py", "content": "import logging\n"}]

    assert not runner._has_in_scope_diff("Create memory pipeline", "Add persistent memory.", files)


def test_github_client_branch_attempt_detection():
    from src.github_client import GitHubClient

    client = GitHubClient("owner", "repo", "token")
    client.session = Mock()
    client.session.get.return_value.json.return_value = [{"number": 28}]

    assert client.has_pull_request_for_branch("bastiao/issue-25")
    client.session.get.assert_called_once()


def test_runner_reports_github_unavailable(tmp_path):
    runner = AutonomousRunner.__new__(AutonomousRunner)
    runner.client = Mock()
    runner.metrics = CycleMetrics(str(tmp_path))
    runner.client.list_issues.side_effect = requests.ConnectionError("network down")

    assert runner.run_once() == {
        "status": "github_unavailable",
        "error": "ConnectionError: network down",
    }


def test_format_plan_includes_scope_and_acceptance_criteria():
    from src.planner import GitHubIssue, Planner

    plan = Planner().build_issue_plan(
        GitHubIssue(32, "Planner", "- [ ] Add `src/planner.py`", [], "open")
    )

    rendered = AutonomousRunner._format_plan(plan)

    assert "src/planner.py" in rendered
    assert "Add `src/planner.py`" in rendered
    assert "inspect:" in rendered


def test_resume_prompt_includes_previous_error():
    from src.planner import IssuePlan, PlanStep

    plan = IssuePlan(
        issue_number=43,
        title="health marker",
        acceptance_criteria=[],
        allowed_paths=["src/health_marker.py"],
        steps=[PlanStep("implement", "Implement", "write")],
    )

    runner = AutonomousRunner.__new__(AutonomousRunner)
    runner._format_plan = AutonomousRunner._format_plan
    rendered = runner._format_plan(plan)
    rendered += (
        "\n\nResume checkpoint: step 0, attempt 2. "
        "Last result: none. Previous error: constant HEALTH_MARKER does not match issue requirement."
    )

    assert "Previous error: constant HEALTH_MARKER does not match issue requirement." in rendered
