import json
import logging

from src.metrics import CycleMetrics
from src.redaction import REDACTED, RedactingFilter, redact, redact_data


def test_redacts_known_token_formats():
    text = (
        "ghp_" + "a" * 36 + " github_pat_" + "B" * 30 + " sk-" + "c" * 20
    )

    result = redact(text)

    assert result == f"{REDACTED} {REDACTED} {REDACTED}"


def test_redacts_authorization_and_key_value_pairs():
    assert "abc123" not in redact("Authorization: token abc123")
    assert "hunter2" not in redact("password=hunter2 next")
    assert "next" in redact("password=hunter2 next")


def test_redacts_configured_secret_values(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "super-secret-value")

    assert "super-secret-value" not in redact("failed with super-secret-value in url")


def test_short_env_values_are_not_replaced(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "abc")

    assert redact("abc stays") == "abc stays"


def test_redact_data_handles_nested_structures():
    data = {"a": ["ghp_" + "x" * 30, {"b": "ok"}], "n": 3}

    assert redact_data(data) == {"a": [REDACTED, {"b": "ok"}], "n": 3}


def test_logging_filter_masks_formatted_message():
    record = logging.LogRecord(
        "t", logging.ERROR, __file__, 1, "token %s", ("ghp_" + "z" * 30,), None
    )

    assert RedactingFilter().filter(record)
    assert record.getMessage() == f"token {REDACTED}"


def test_metrics_record_is_redacted(tmp_path):
    metrics = CycleMetrics(str(tmp_path))
    metrics.record({"status": "failed", "error": "bad ghp_" + "q" * 30}, 0.1)

    line = (tmp_path / "cycles.jsonl").read_text(encoding="utf-8")
    assert "ghp_" not in line
    assert REDACTED in line
    assert "ghp_" not in (tmp_path / "status.json").read_text(encoding="utf-8")


def test_metrics_rotation_keeps_bounded_backups(tmp_path):
    metrics = CycleMetrics(str(tmp_path), max_bytes=200, backups=2)

    for index in range(40):
        metrics.record({"status": "no_open_issues", "n": index}, 0.1)

    names = sorted(path.name for path in tmp_path.glob("cycles.jsonl*"))
    assert names == ["cycles.jsonl", "cycles.jsonl.1", "cycles.jsonl.2"]
    newest = json.loads((tmp_path / "cycles.jsonl").read_text().splitlines()[-1])
    assert newest["n"] == 39


def test_metrics_without_backups_discards_old_file(tmp_path):
    metrics = CycleMetrics(str(tmp_path), max_bytes=100, backups=0)

    for index in range(10):
        metrics.record({"status": "x", "n": index}, 0.1)

    assert [path.name for path in tmp_path.glob("cycles.jsonl*")] == ["cycles.jsonl"]
