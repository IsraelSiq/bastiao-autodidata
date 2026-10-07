"""Durable cycle metrics for operations and diagnosis."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional


class CycleMetrics:
    """Append one JSON record per autonomous cycle."""

    def __init__(self, directory: str):
        self.path = Path(directory) / "cycles.jsonl"
        self.status_path = Path(directory) / "status.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, result: dict, duration_seconds: float) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(duration_seconds, 3),
            **result,
        }
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
