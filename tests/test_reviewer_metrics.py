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
