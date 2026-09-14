"""Structured state for an autonomous issue task."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path

from .planner import IssuePlan


@dataclass
class TaskExecutionState:
    """Tracks plan progress independently from model messages."""

    issue_number: int
    plan: dict = field(default_factory=dict)
    status: str = "planned"
    current_step: int = 0
    attempts: int = 0
    error: str = ""
    result: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def start_step(self) -> None:
        self.status = "running"
        self.attempts += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def complete_step(self) -> None:
        self.current_step += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def checkpoint(self, result: str = "") -> None:
        """Persist the latest successful observation without advancing the plan."""
        self.result = result
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def complete(self) -> None:
        self.status = "completed"
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.error = error
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def save(self, directory: str) -> Path:
        path = Path(directory) / f"issue-{self.issue_number}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str) -> "TaskExecutionState":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


def create_task_state(plan: IssuePlan) -> TaskExecutionState:
    return TaskExecutionState(issue_number=plan.issue_number, plan=plan.to_dict())
