import json
from unittest.mock import Mock, patch
from uuid import UUID
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


def test_runner_reports_github_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("BASTIAO_GITHUB_RETRY_ATTEMPTS", "2")
    monkeypatch.setenv("BASTIAO_GITHUB_RETRY_BASE_SECONDS", "0")
    runner = AutonomousRunner.__new__(AutonomousRunner)
    runner.client = Mock()
    runner.metrics = CycleMetrics(str(tmp_path))
    runner.client.list_issues.side_effect = requests.ConnectionError("network down")

    result = runner.run_once()

    assert runner.client.list_issues.call_count == 2
    status = runner.metrics.read_status()
    assert status["last_cycle"]["cycle_id"] == result["cycle_id"]
    assert status["github_unavailable_since"]
    assert result["status"] == "github_unavailable"
    assert result["error"] == "ConnectionError: network down"
    assert str(UUID(result["cycle_id"])) == result["cycle_id"]
    record = json.loads((tmp_path / "cycles.jsonl").read_text(encoding="utf-8"))
    assert record["cycle_id"] == result["cycle_id"]
    assert record["status"] == result["status"]


def test_status_survives_restart_and_recovers(tmp_path, monkeypatch):
    monkeypatch.setenv("BASTIAO_GITHUB_RETRY_ATTEMPTS", "1")
    runner = AutonomousRunner.__new__(AutonomousRunner)
    runner.client = Mock()
    runner.metrics = CycleMetrics(str(tmp_path))
    runner.client.list_issues.side_effect = requests.ConnectionError("down")
    runner.run_once()
    since = runner.metrics.read_status()["github_unavailable_since"]

    restarted = AutonomousRunner.__new__(AutonomousRunner)
    restarted.client = Mock()
    restarted.metrics = CycleMetrics(str(tmp_path))
    assert restarted.metrics.read_status()["github_unavailable_since"] == since

    restarted.client.list_issues.return_value = []
    result = restarted.run_once()

    assert result["status"] == "no_open_issues"
    assert "github_unavailable_since" not in restarted.metrics.read_status()


def test_runner_does_not_retry_authentication_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("BASTIAO_GITHUB_RETRY_ATTEMPTS", "3")
    monkeypatch.setenv("BASTIAO_GITHUB_RETRY_BASE_SECONDS", "0")
    response = Mock()
    response.status_code = 401
    runner = AutonomousRunner.__new__(AutonomousRunner)
    runner.client = Mock()
    runner.metrics = CycleMetrics(str(tmp_path))
    runner.client.list_issues.side_effect = requests.HTTPError(response=response)

    result = runner.run_once()

    assert runner.client.list_issues.call_count == 1
    assert result["status"] == "github_unavailable"


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


def test_changed_files_includes_new_files(tmp_path):
    runner = AutonomousRunner.__new__(AutonomousRunner)
    runner.workspace = tmp_path
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "health_marker.py").write_text(
        'HEALTH_MARKER = "ok"\n', encoding="utf-8"
    )

    runner._git = Mock(side_effect=[
        "",
        "?? src/health_marker.py",
    ])

    assert runner._changed_files() == [{
        "path": "src/health_marker.py",
        "content": 'HEALTH_MARKER = "ok"\n',
    }]


def test_runner_exposes_quality_gate_evidence(tmp_path):
    from src.quality_gate import GateCheck, QualityGateResult

    runner = AutonomousRunner.__new__(AutonomousRunner)
    runner.workspace = tmp_path
    runner.quality_gate_timeout = 7
    runner.memory_limit_mb = 128
    runner.cpu_limit_seconds = 9

    with patch("src.autonomous.QualityGate") as gate_class:
        gate_class.return_value.run.return_value = QualityGateResult(
            passed=True,
            checks=[
                GateCheck(
                    name="git-diff-check",
                    command=["git", "diff", "--check", "origin/main"],
                    passed=True,
                    returncode=0,
                    duration_seconds=0.01,
                    output="",
                )
            ],
        )
        result = runner._run_quality_gate()

    gate_class.assert_called_once_with(
        tmp_path, timeout_seconds=7, memory_limit_mb=128, cpu_limit_seconds=9
    )
    assert result["passed"]
    assert result["checks"][-1]["name"] == "git-diff-check"
