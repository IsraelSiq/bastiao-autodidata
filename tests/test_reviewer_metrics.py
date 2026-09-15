import json

from src.metrics import CycleMetrics
from src.reviewer import Reviewer


def test_reviewer_rejects_out_of_scope_patch():
    result = Reviewer().review([{"path": "src/other.py"}], False, True)

    assert not result.approved
    assert "patch is outside issue scope" in result.reasons


def test_cycle_metrics_appends_json_record(tmp_path):
    metrics = CycleMetrics(str(tmp_path))
    metrics.record({"status": "pending_approval", "issue": 41}, 0.25)

    record = json.loads((tmp_path / "cycles.jsonl").read_text(encoding="utf-8"))
    assert record["status"] == "pending_approval"
    assert record["duration_seconds"] == 0.25


def test_reviewer_rejects_wrong_explicit_constant(tmp_path):
    target = tmp_path / "src" / "health_marker.py"
    target.parent.mkdir()
    target.write_text("HEALTH_MARKER = True\n", encoding="utf-8")

    result = Reviewer().review(
        [{"path": "src/health_marker.py"}],
        True,
        True,
        issue_text="Create `src/health_marker.py` with constant `HEALTH_MARKER = \"ok\"`.",
        workspace=str(tmp_path),
    )

    assert not result.approved
    assert any("does not match issue requirement" in reason for reason in result.reasons)


def test_reviewer_rejects_unquoted_constant_value(tmp_path):
    target = tmp_path / "src" / "health_marker.py"
    target.parent.mkdir()
    target.write_text("HEALTH_MARKER = ok\n", encoding="utf-8")

    result = Reviewer().review(
        [{"path": "src/health_marker.py"}],
        True,
        True,
        issue_text="Create `src/health_marker.py` with constant `HEALTH_MARKER = \"ok\"`.",
        workspace=str(tmp_path),
    )

    assert not result.approved
    assert any("does not match issue requirement" in reason for reason in result.reasons)
