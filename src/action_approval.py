"""Audited, expiring approvals for sensitive autonomous actions."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import uuid


class ActionClass(str, Enum):
    AUTOMATIC = "automatic"
    APPROVAL = "approval"
    BLOCKED = "blocked"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _is_sensitive_path(path: Path) -> bool:
    sensitive_names = {"token", "tokens", "api_key", "access_token", "private_key"}
    for part in path.parts:
        name = part.lower()
        if name.startswith(".env") or any(
            marker in name for marker in ("secret", "credential", "password")
        ):
            return True
        if name in sensitive_names or Path(name).suffix in {".pem", ".key", ".p12", ".pfx"}:
            return True
    return False


def _safe_command_context(argv: list[str]) -> str:
    rendered = []
    redact_next = False
    sensitive_markers = ("token", "secret", "password", "credential", "api_key", "private_key")
    for argument in argv:
        if redact_next:
            rendered.append("[redacted]")
            redact_next = False
            continue
        lowered = argument.lower()
        if any(marker in lowered.split("=", 1)[0] for marker in sensitive_markers):
            if "=" in argument:
                rendered.append(argument.split("=", 1)[0] + "=[redacted]")
            else:
                rendered.append(argument)
                redact_next = True
            continue
        if argument in {"-e", "--eval"} and Path(argv[0]).name.lower() == "node":
            rendered.extend([argument, "[inline code redacted]"])
            redact_next = True
            continue
        rendered.append(re.sub(r"https?://\S+", "[URL redacted]", argument))
    context = shlex.join(rendered)
    return context if len(context) <= 500 else context[:500] + "...[truncated]"


def _docker_block_reason(argv: list[str]) -> str | None:
    args = argv[1:]
    if not args:
        return "Docker command is not allowlisted"
    if args[0] == "compose":
        if len(args) > 1 and args[1] in {"config", "ps", "logs", "images"}:
            return None
        return "mutating Docker Compose operations are blocked"
    if args[0] in {"version", "info", "ps", "images", "inspect", "logs", "stats"}:
        return None
    return f"Docker operation {args[0]} is blocked"


def _references_external_path(arguments: list[str], repo_root: Path) -> bool:
    for argument in arguments:
        candidate_text = argument.split("=", 1)[1] if argument.startswith("--") and "=" in argument else argument
        if candidate_text.startswith("-") or "://" in candidate_text:
            continue
        candidate = Path(candidate_text).expanduser()
        resolved = candidate if candidate.is_absolute() else repo_root / candidate
        resolved = resolved.resolve()
        if resolved != repo_root and repo_root not in resolved.parents:
            return True
    return False


def classify_action(action: str, repo_path: str | Path) -> tuple[ActionClass, str, str]:
    """Classify a tool request and return its class, safe context, and fingerprint."""
    fingerprint = hashlib.sha256(action.encode("utf-8")).hexdigest()
    parts = action.strip().split(maxsplit=1)
    if not parts:
        return ActionClass.BLOCKED, "empty action", fingerprint

    operation = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    repo_root = Path(repo_path).resolve()

    if operation == "read":
        target = args.strip()
        if not target:
            return ActionClass.BLOCKED, "read path not supplied", fingerprint
        candidate = Path(target)
        if candidate.is_absolute():
            return ActionClass.BLOCKED, "read outside workspace", fingerprint
        resolved = (repo_root / candidate).resolve()
        if resolved != repo_root and repo_root not in resolved.parents:
            return ActionClass.BLOCKED, "read outside workspace", fingerprint
        if _is_sensitive_path(resolved.relative_to(repo_root)):
            return ActionClass.BLOCKED, "credential or secret file", fingerprint
        return ActionClass.AUTOMATIC, f"workspace file {resolved.relative_to(repo_root).as_posix()}", fingerprint

    if operation in {"search", "list", "complete"}:
        return ActionClass.AUTOMATIC, operation, fingerprint

    if operation == "write":
        target = args.split(maxsplit=1)[0] if args else ""
        if not target:
            return ActionClass.AUTOMATIC, "write (path not supplied)", fingerprint
        candidate = Path(target)
        if candidate.is_absolute():
            return ActionClass.BLOCKED, "write outside workspace", fingerprint
        resolved = (repo_root / candidate).resolve()
        if resolved != repo_root and repo_root not in resolved.parents:
            return ActionClass.BLOCKED, "write outside workspace", fingerprint
        normalized = resolved.relative_to(repo_root).as_posix()
        lower_path = normalized.lower()
        if _is_sensitive_path(Path(normalized)):
            return ActionClass.BLOCKED, "credential or secret file", fingerprint
        if (
            Path(normalized).suffix.lower() in {".json", ".toml", ".ini", ".cfg", ".conf", ".yaml", ".yml"}
            or lower_path.endswith(("requirements.txt", "dockerfile"))
        ):
            return ActionClass.APPROVAL, f"configuration file {normalized}", fingerprint
        return ActionClass.AUTOMATIC, f"workspace file {normalized}", fingerprint

    if operation != "run":
        return ActionClass.BLOCKED, f"unknown action {operation}", fingerprint

    if re.search(r"(?<!\w)(?:[A-Za-z]:[\\/]|\\\\)", args):
        return ActionClass.BLOCKED, "command path escapes workspace", fingerprint
    try:
        argv = shlex.split(args)
    except ValueError:
        return ActionClass.BLOCKED, "invalid command syntax", fingerprint
    if not argv:
        return ActionClass.BLOCKED, "empty command", fingerprint

    executable = Path(argv[0]).name.lower()
    if executable in {
        "sudo", "su", "rm", "rmdir", "mkfs", "dd", "shutdown", "reboot",
        "poweroff", "kill", "killall", "chmod", "chown", "mount", "umount",
        "podman",
    }:
        return ActionClass.BLOCKED, f"blocked system command {executable}", fingerprint
    if executable == "docker":
        reason = _docker_block_reason(argv)
        if reason:
            return ActionClass.BLOCKED, reason, fingerprint
        return (
            ActionClass.APPROVAL,
            f"Docker inspection: {_safe_command_context(argv)}",
            fingerprint,
        )
    if executable == "git" and len(argv) > 1 and argv[1] in {
        "push", "commit", "reset", "clean", "checkout", "switch", "branch",
    }:
        return ActionClass.BLOCKED, f"blocked git command {argv[1]}", fingerprint
    if executable == "git" and any(
        option in argv for option in ("--no-index", "--git-dir", "--work-tree")
    ):
        return ActionClass.BLOCKED, "Git command can access outside the workspace", fingerprint
    if (
        (executable in {"pip", "pip3"} and len(argv) > 1 and argv[1] == "install")
        or (
            executable in {"python", "python3"}
            and len(argv) > 3
            and argv[1:3] == ["-m", "pip"]
            and argv[3] == "install"
        )
        or (
            executable == "npm"
            and len(argv) > 1
            and argv[1] in {"install", "ci", "update"}
        )
    ):
        return (
            ActionClass.APPROVAL,
            f"dependency installation: {_safe_command_context(argv)}",
            fingerprint,
        )
    if executable in {"python", "python3"}:
        if len(argv) > 2 and argv[1:3] in (
            ["-m", "pytest"],
            ["-m", "compileall"],
            ["-m", "py_compile"],
        ):
            if _references_external_path(argv[3:], repo_root):
                return ActionClass.BLOCKED, "command path escapes workspace", fingerprint
            return ActionClass.AUTOMATIC, f"verification command {argv[1]} {argv[2]}", fingerprint
        return ActionClass.BLOCKED, "Python execution is limited to test and compile commands", fingerprint
    if executable in {"pytest", "git"}:
        if _references_external_path(argv[1:], repo_root):
            return ActionClass.BLOCKED, "command path escapes workspace", fingerprint
        return ActionClass.AUTOMATIC, f"command {executable}", fingerprint
    if executable in {"npm", "node"}:
        return (
            ActionClass.APPROVAL,
            f"JavaScript execution: {_safe_command_context(argv)}",
            fingerprint,
        )
    return ActionClass.BLOCKED, f"command {executable} is not allowlisted", fingerprint


class ActionApprovalStore:
    """Persist requests, single-use decisions, expiry, and an append-only audit trail."""

    def __init__(
        self,
        request_path: str | Path | None = None,
        audit_path: str | Path | None = None,
        request_ttl_seconds: int | None = None,
        approval_ttl_seconds: int | None = None,
    ):
        state_dir = Path(os.getenv("BASTIAO_STATE_DIR", "/var/lib/bastiao"))
        self.request_path = Path(
            request_path or os.getenv(
                "BASTIAO_ACTION_APPROVAL_FILE", str(state_dir / "action-approvals.json")
            )
        )
        self.audit_path = Path(
            audit_path or os.getenv(
                "BASTIAO_ACTION_AUDIT_FILE", str(state_dir / "action-approval-audit.jsonl")
            )
        )
        self.request_ttl_seconds = (
            request_ttl_seconds
            if request_ttl_seconds is not None
            else int(os.getenv("BASTIAO_APPROVAL_REQUEST_TTL_SECONDS", "86400"))
        )
        self.approval_ttl_seconds = (
            approval_ttl_seconds
            if approval_ttl_seconds is not None
            else int(os.getenv("BASTIAO_ACTION_APPROVAL_TTL_SECONDS", "3600"))
        )
        if self.request_ttl_seconds <= 0 or self.approval_ttl_seconds <= 0:
            raise ValueError("approval TTL values must be positive")

    def _read(self) -> list[dict]:
        try:
            data = json.loads(self.request_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise ValueError("action approval file must contain a JSON list of records")
        return data

    def _write(self, records: list[dict]) -> None:
        self.request_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.request_path.with_suffix(self.request_path.suffix + ".tmp")
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(records, stream, indent=2, sort_keys=True)
        temporary.replace(self.request_path)
        if os.name != "nt":
            os.chmod(self.request_path, 0o600)

    def _audit(self, event: str, record: dict, actor: str = "agent") -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": _iso(_utc_now()),
            "event": event,
            "request_id": record["request_id"],
            "issue_number": record["issue_number"],
            "action": record["action"],
            "target": record["target"],
            "actor": actor,
        }
        descriptor = os.open(
            self.audit_path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, sort_keys=True) + "\n")
        if os.name != "nt":
            os.chmod(self.audit_path, 0o600)

    def request(self, issue_number: int, action: str, target: str, fingerprint: str) -> dict:
        now = _utc_now()
        records = self._read()
        for record in records:
            if (
                record.get("issue_number") == issue_number
                and record.get("action") == action
                and record.get("fingerprint") == fingerprint
                and record.get("status") in {"pending", "approved"}
            ):
                expiry_key = "request_expires_at" if record["status"] == "pending" else "expires_at"
                if _parse_datetime(record[expiry_key]) > now:
                    return record

        record = {
            "request_id": str(uuid.uuid4()),
            "issue_number": issue_number,
            "action": action,
            "target": target,
            "fingerprint": fingerprint,
            "status": "pending",
            "requested_at": _iso(now),
            "request_expires_at": _iso(now + timedelta(seconds=self.request_ttl_seconds)),
            "approver": None,
            "decided_at": None,
            "expires_at": None,
        }
        records.append(record)
        self._write(records)
        self._audit("requested", record)
        return record

    def decide(self, request_id: str, approver: str, approved: bool) -> dict:
        if not approver.strip():
            raise ValueError("approver name is required")
        records = self._read()
        record = next((item for item in records if item["request_id"] == request_id), None)
        if record is None:
            raise ValueError("approval request not found")
        now = _utc_now()
        if record["status"] != "pending":
            raise ValueError(f"approval request is already {record['status']}")
        if _parse_datetime(record["request_expires_at"]) <= now:
            record["status"] = "expired"
            self._write(records)
            self._audit("request_expired", record)
            raise ValueError("approval request has expired")
        record["status"] = "approved" if approved else "denied"
        record["approver"] = approver.strip()
        record["decided_at"] = _iso(now)
        record["expires_at"] = (
            _iso(now + timedelta(seconds=self.approval_ttl_seconds)) if approved else None
        )
        self._write(records)
        self._audit(record["status"], record, approver.strip())
        return record

    def authorize(
        self, issue_number: int, action: str, target: str, fingerprint: str
    ) -> tuple[bool, dict]:
        """Consume one unexpired approval or create a pending request without side effects."""
        now = _utc_now()
        records = self._read()
        for record in reversed(records):
            if (
                record.get("issue_number") != issue_number
                or record.get("action") != action
                or record.get("fingerprint") != fingerprint
            ):
                continue
            if record["status"] == "denied":
                return False, record
            if record["status"] == "approved":
                if _parse_datetime(record["expires_at"]) <= now:
                    record["status"] = "expired"
                    self._write(records)
                    self._audit("approval_expired", record)
                    break
                record["status"] = "consumed"
                record["consumed_at"] = _iso(now)
                self._write(records)
                self._audit("consumed", record, record["approver"])
                return True, record
            if record["status"] == "pending" and _parse_datetime(
                record["request_expires_at"]
            ) > now:
                return False, record

        request = self.request(issue_number, action, target, fingerprint)
        return False, request

    def list_requests(self) -> list[dict]:
        return self._read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Review Bastiao sensitive-action approvals.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list approval requests")
    for name in ("approve", "deny"):
        command = commands.add_parser(name)
        command.add_argument("request_id")
        command.add_argument("--approver", required=name == "approve")
    args = parser.parse_args()
    store = ActionApprovalStore()
    if args.command == "list":
        print(json.dumps(store.list_requests(), indent=2, sort_keys=True))
        return 0
    try:
        record = store.decide(
            args.request_id,
            args.approver or "operator",
            args.command == "approve",
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
