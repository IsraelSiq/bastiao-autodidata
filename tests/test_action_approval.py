import json
import os
from pathlib import Path

import pytest

from src.action_approval import ActionApprovalStore, ActionClass, classify_action
from src.process import ProcessResult
from src.tools import ToolHandler


def test_classifies_sensitive_and_blocked_actions(tmp_path: Path):
    assert classify_action("write pyproject.toml [project]", tmp_path)[0] is ActionClass.APPROVAL
    assert classify_action("run pip install package", tmp_path)[0] is ActionClass.APPROVAL
    assert classify_action("run docker run image", tmp_path)[0] is ActionClass.BLOCKED
    assert classify_action("run docker ps", tmp_path)[0] is ActionClass.APPROVAL
    assert classify_action("run git push origin main", tmp_path)[0] is ActionClass.BLOCKED
    assert classify_action("run python -c 'import os'", tmp_path)[0] is ActionClass.BLOCKED
    assert classify_action("run python -m pytest -q", tmp_path)[0] is ActionClass.AUTOMATIC
    assert classify_action("run git diff --no-index a b", tmp_path)[0] is ActionClass.BLOCKED
    assert classify_action(r"run pytest C:\outside\test.py", tmp_path)[0] is ActionClass.BLOCKED
    _, context, _ = classify_action(
        "run pip install --token=abc123 package",
        tmp_path,
    )
    assert "abc123" not in context
    assert "package" in context


@pytest.mark.parametrize(
    "action",
    [
        "read ../outside.txt",
        "read .env",
        "read src/client_secret.py",
        "write ../outside.txt secret",
        "write credentials.json secret",
    ],
)
def test_classifies_workspace_escape_and_secrets_as_blocked(tmp_path: Path, action: str):
    assert classify_action(action, tmp_path)[0] is ActionClass.BLOCKED


def test_blocks_test_commands_that_reference_paths_outside_workspace(tmp_path: Path):
    assert classify_action("run pytest ../outside-test.py", tmp_path)[0] is ActionClass.BLOCKED
    assert classify_action("run python -m compileall ../../outside", tmp_path)[
        0
    ] is ActionClass.BLOCKED


def test_store_persists_expiring_single_use_approval_and_audit(tmp_path: Path):
    store = ActionApprovalStore(
        tmp_path / "requests.json",
        tmp_path / "audit.jsonl",
        request_ttl_seconds=60,
        approval_ttl_seconds=60,
    )
    pending = store.request(29, "dependency_install", "package setup.py", "fingerprint")
    assert store.request(29, "dependency_install", "package setup.py", "fingerprint")[
        "request_id"
    ] == pending["request_id"]

    approved = store.decide(pending["request_id"], "operator@example.test", True)
    assert approved["status"] == "approved"
    allowed, consumed = store.authorize(
        29, "dependency_install", "package setup.py", "fingerprint"
    )
    assert allowed
    assert consumed["status"] == "consumed"

    allowed_again, replacement = store.authorize(
        29, "dependency_install", "package setup.py", "fingerprint"
    )
    assert not allowed_again
    assert replacement["status"] == "pending"
    audit = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert [entry["event"] for entry in audit] == [
        "requested",
        "approved",
        "consumed",
        "requested",
    ]
    assert audit[1]["actor"] == "operator@example.test"
    assert "fingerprint" not in (tmp_path / "audit.jsonl").read_text()
    if os.name != "nt":
        assert (tmp_path / "requests.json").stat().st_mode & 0o777 == 0o600


def test_denial_is_persisted_and_never_authorizes(tmp_path: Path):
    store = ActionApprovalStore(tmp_path / "requests.json", tmp_path / "audit.jsonl")
    request = store.request(29, "publish_changes", "bastiao/issue-29", "sha")
    store.decide(request["request_id"], "reviewer", False)

    allowed, record = store.authorize(29, "publish_changes", "bastiao/issue-29", "sha")

    assert not allowed
    assert record["status"] == "denied"


def test_expired_request_cannot_be_approved(tmp_path: Path):
    store = ActionApprovalStore(tmp_path / "requests.json", tmp_path / "audit.jsonl")
    request = store.request(29, "publish_changes", "branch", "sha")
    records = store._read()
    records[0]["request_expires_at"] = "2000-01-01T00:00:00+00:00"
    store._write(records)

    with pytest.raises(ValueError, match="has expired"):
        store.decide(request["request_id"], "operator", True)

    assert store.list_requests()[0]["status"] == "expired"


def test_tool_handler_stops_sensitive_actions_until_exact_approval(tmp_path: Path):
    store = ActionApprovalStore(tmp_path / "requests.json", tmp_path / "audit.jsonl")
    handler = ToolHandler(str(tmp_path), issue_number=29, approval_store=store)

    result = handler.execute("write pyproject.toml [project]")

    assert result.startswith("ERROR: Sensitive action requires human approval")
    request = store.list_requests()[0]
    assert request["status"] == "pending"
    assert not (tmp_path / "pyproject.toml").exists()

    store.decide(request["request_id"], "operator", True)
    assert handler.execute("write pyproject.toml [project]") == "OK: Wrote pyproject.toml"
    assert (tmp_path / "pyproject.toml").read_text() == "[project]"


def test_tool_handler_fails_closed_without_approval_context(tmp_path: Path):
    handler = ToolHandler(str(tmp_path))

    assert "requires an approval store and issue number" in handler.execute(
        "run pip install package"
    )
    assert not list(tmp_path.iterdir())


def test_tool_handler_executes_package_install_only_after_exact_approval(
    tmp_path: Path, monkeypatch
):
    store = ActionApprovalStore(tmp_path / "requests.json", tmp_path / "audit.jsonl")
    handler = ToolHandler(str(tmp_path), issue_number=29, approval_store=store)
    action = "run pip install package"

    assert "requires human approval" in handler.execute(action)
    request = store.list_requests()[0]
    store.decide(request["request_id"], "operator", True)

    def fake_run_bounded(argv, **kwargs):
        assert argv == ["pip", "install", "package"]
        return ProcessResult(0, "installed", "")

    monkeypatch.setattr("src.tools.run_bounded", fake_run_bounded)
    assert handler.execute(action) == "installed"
    assert store.list_requests()[0]["status"] == "consumed"


def test_docker_inspection_requires_approval_but_mutations_stay_blocked(
    tmp_path: Path, monkeypatch
):
    store = ActionApprovalStore(tmp_path / "requests.json", tmp_path / "audit.jsonl")
    handler = ToolHandler(str(tmp_path), issue_number=29, approval_store=store)

    assert "requires human approval" in handler.execute("run docker ps")
    request = store.list_requests()[0]
    store.decide(request["request_id"], "operator", True)
    monkeypatch.setattr(
        "src.tools.run_bounded",
        lambda argv, **kwargs: ProcessResult(0, "container list", ""),
    )

    assert handler.execute("run docker ps") == "container list"
    assert handler.execute("run docker compose up -d").startswith("ERROR: Action blocked")
    assert handler.execute("run docker system prune -a").startswith("ERROR: Action blocked")


def test_tool_handler_blocks_dangerous_actions_before_side_effects(tmp_path: Path):
    handler = ToolHandler(str(tmp_path), issue_number=29, approval_store=ActionApprovalStore(
        tmp_path / "requests.json", tmp_path / "audit.jsonl"
    ))

    assert handler.execute("run docker run image").startswith("ERROR: Action blocked")
    assert handler.execute("run docker compose down -v").startswith("ERROR: Action blocked")
    assert handler.execute("read ../outside.txt").startswith("ERROR: Action blocked")
    assert not list(tmp_path.iterdir())
