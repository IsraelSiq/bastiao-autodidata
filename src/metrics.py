"""Durable cycle metrics for operations and diagnosis."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Optional

from .redaction import redact_data


class CycleMetrics:
    """Append one redacted JSON record per autonomous cycle, with size-based retention."""

    def __init__(
        self,
        directory: str,
        max_bytes: Optional[int] = None,
        backups: Optional[int] = None,
    ):
        self.path = Path(directory) / "cycles.jsonl"
        self.status_path = Path(directory) / "status.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_bytes = (
            max_bytes
            if max_bytes is not None
            else int(os.getenv("BASTIAO_METRICS_MAX_BYTES", str(5 * 1024 * 1024)))
        )
        self.backups = (
            backups if backups is not None else int(os.getenv("BASTIAO_METRICS_BACKUPS", "5"))
        )

    def _rotate(self) -> None:
        """Keep at most `backups` older files: cycles.jsonl.1 is the newest."""
        if self.max_bytes <= 0 or not self.path.exists():
            return
        if self.path.stat().st_size < self.max_bytes:
            return
        oldest = self.path.with_name(f"{self.path.name}.{self.backups}")
        if self.backups <= 0:
            self.path.unlink()
            return
        oldest.unlink(missing_ok=True)
        for index in range(self.backups - 1, 0, -1):
            source = self.path.with_name(f"{self.path.name}.{index}")
            if source.exists():
                source.replace(self.path.with_name(f"{self.path.name}.{index + 1}"))
        self.path.replace(self.path.with_name(f"{self.path.name}.1"))

    def record(self, result: dict, duration_seconds: float) -> None:
        entry = redact_data(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(duration_seconds, 3),
                **result,
            }
        )
        self._rotate()
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, sort_keys=True) + "\n")
        self._write_status(entry)

    def _write_status(self, entry: dict) -> None:
        """Atomically persist the latest cycle so restarts and operators can read it."""
        status = {"last_cycle": entry}
        if entry.get("status") == "github_unavailable":
            status["github_unavailable_since"] = (
                self.read_status().get("github_unavailable_since") or entry["timestamp"]
            )
        temporary = self.status_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(status, sort_keys=True), encoding="utf-8")
        temporary.replace(self.status_path)

    def read_status(self) -> dict:
        try:
            return json.loads(self.status_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return {}
