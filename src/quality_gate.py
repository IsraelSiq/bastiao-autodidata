"""Deterministic quality gate executed before publishing a pull request."""

from dataclasses import dataclass
import json
import sys
import time
from pathlib import Path

from .process import run_bounded, sanitized_env


@dataclass(frozen=True)
class GateCheck:
    """Result of one quality-gate command."""

    name: str
    command: list[str]
    passed: bool
    returncode: int | None
    duration_seconds: float
    output: str
    timed_out: bool = False
    limit_exceeded: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "command": self.command,
            "passed": self.passed,
            "returncode": self.returncode,
            "duration_seconds": self.duration_seconds,
            "output": self.output,
            "timed_out": self.timed_out,
            "limit_exceeded": self.limit_exceeded,
        }


@dataclass(frozen=True)
class QualityGateResult:
    """Complete quality-gate decision and its evidence."""

    passed: bool
    checks: list[GateCheck]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
        }

    def failure_summary(self) -> str:
        failed = [check for check in self.checks if not check.passed]
        details = []
        for check in failed:
            if check.limit_exceeded:
                detail = f"{check.limit_exceeded} resource limit"
            elif check.timed_out:
                detail = "timeout"
            else:
                detail = f"exit {check.returncode}"
            details.append(f"{check.name}: {detail}")
        return "; ".join(details)


class QualityGate:
    """Discover and run repository quality checks with bounded execution."""

    def __init__(
        self,
        workspace: str | Path,
        timeout_seconds: int = 120,
        memory_limit_mb: int = 0,
        cpu_limit_seconds: int = 0,
    ):
        self.workspace = Path(workspace).resolve()
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self.cpu_limit_seconds = cpu_limit_seconds

    def _commands(self) -> list[tuple[str, list[str]]]:
        commands: list[tuple[str, list[str]]] = []
        if (self.workspace / "tests").is_dir():
            commands.append(("pytest", [sys.executable, "-m", "pytest", "tests", "-q"]))
        if any(self.workspace.glob("**/*.py")):
            commands.append(("compileall", [sys.executable, "-m", "compileall", "-q", "."]))

        package_file = self.workspace / "package.json"
        if package_file.is_file():
            package = json.loads(package_file.read_text(encoding="utf-8"))
            scripts = package.get("scripts", {})
            for name in ("lint", "typecheck"):
                if name in scripts:
                    commands.append((f"npm:{name}", ["npm", "run", name]))

        commands.append(("git-diff-check", ["git", "diff", "--check", "origin/main"]))
        return commands

    def run(self) -> QualityGateResult:
        checks: list[GateCheck] = []
        for name, command in self._commands():
            started = time.monotonic()
            try:
                completed = run_bounded(
                    command,
                    cwd=str(self.workspace),
                    timeout=self.timeout_seconds,
                    env=sanitized_env(),
                    memory_mb=self.memory_limit_mb,
                    cpu_seconds=self.cpu_limit_seconds,
                )
                duration = round(time.monotonic() - started, 3)
                output = (completed.stdout + completed.stderr).strip()
                if completed.output_truncated:
                    output += "\n[output truncated at 1000000 bytes per stream]"
                if completed.limit_exceeded:
                    output += f"\n[{completed.limit_exceeded} resource limit reached]"
                checks.append(
                    GateCheck(
                        name=name,
                        command=command,
                        passed=(
                            not completed.timed_out
                            and completed.returncode == 0
                            and completed.limit_exceeded is None
                        ),
                        returncode=completed.returncode,
                        duration_seconds=duration,
                        output=output[-10000:],
                        timed_out=completed.timed_out,
                        limit_exceeded=completed.limit_exceeded,
                    )
                )
            except OSError as error:
                checks.append(
                    GateCheck(
                        name=name,
                        command=command,
                        passed=False,
                        returncode=None,
                        duration_seconds=round(time.monotonic() - started, 3),
                        output=f"{type(error).__name__}: {error}",
                    )
                )
        return QualityGateResult(all(check.passed for check in checks), checks)
