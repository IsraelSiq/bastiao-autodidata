"""Durable cycle metrics for operations and diagnosis."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional


class CycleMetrics:
    """Append one JSON record per autonomous cycle."""

    def __init__(self, directory: str):
        self.path = Path(directory) / "cycles.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, result: dict, duration_seconds: float) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(duration_seconds, 3),
            **result,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, sort_keys=True) + "\n")
