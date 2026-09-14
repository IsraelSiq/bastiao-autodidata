import json

from src.planner import GitHubIssue, IssuePlan, Planner
from src.task_state import TaskExecutionState, create_task_state


def test_planner_builds_structured_steps_and_paths():
    issue = GitHubIssue(
        number=32,
        title="Separate planner and executor",
        body="- [ ] Add `src/task_state.py`\n- [ ] Add tests",
        labels=[],
        state="open",
    )

    plan = Planner().build_issue_plan(issue)

    assert plan.issue_number == 32
    assert plan.allowed_paths == ["src/task_state.py"]
    assert [step.id for step in plan.steps] == ["inspect", "implement", "verify", "review"]
    restored = IssuePlan.from_dict(plan.to_dict())
    assert restored.steps[1].action == "write only allowed files"


def test_task_state_advances_and_persists(tmp_path):
    state = TaskExecutionState(issue_number=32)
    state.start_step()
    state.complete_step()
    state.save(str(tmp_path))

    loaded = TaskExecutionState.load(str(tmp_path / "issue-32.json"))

    assert loaded.status == "running"
    assert loaded.current_step == 1
    assert loaded.attempts == 1


def test_task_state_persists_plan_and_checkpoint(tmp_path):
    issue = GitHubIssue(32, "Planner", "- [ ] Add `src/planner.py`", [], "open")
    state = create_task_state(Planner().build_issue_plan(issue))
    state.start_step()
    state.checkpoint("inspection complete")
    state.save(str(tmp_path))

    loaded = TaskExecutionState.load(str(tmp_path / "issue-32.json"))

    assert loaded.plan["issue_number"] == 32
    assert loaded.result == "inspection complete"
