"""Deterministic quality gate executed before publishing a pull request."""

from dataclasses import dataclass
import json
import subprocess
import sys
import time
from pathlib import Path


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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "command": self.command,
            "passed": self.passed,
            "returncode": self.returncode,
            "duration_seconds": self.duration_seconds,
            "output": self.output,
            "timed_out": self.timed_out,
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
        return "; ".join(
            f"{check.name}: "
            f"{'timeout' if check.timed_out else f'exit {check.returncode}'}"
            for check in failed
        )


class QualityGate:
    """Discover and run repository quality checks with bounded execution."""

    def __init__(self, workspace: str | Path, timeout_seconds: int = 120):
        self.workspace = Path(workspace).resolve()
        self.timeout_seconds = timeout_seconds

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
                completed = subprocess.run(
                    command,
                    cwd=self.workspace,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                output = (completed.stdout + completed.stderr).strip()
                checks.append(
                    GateCheck(
                        name=name,
                        command=command,
                        passed=completed.returncode == 0,
                        returncode=completed.returncode,
                        duration_seconds=round(time.monotonic() - started, 3),
                        output=output[-10000:],
                    )
                )
            except subprocess.TimeoutExpired as error:
                output = self._as_text(error.stdout) + self._as_text(error.stderr)
                checks.append(
                    GateCheck(
                        name=name,
                        command=command,
                        passed=False,
                        returncode=None,
                        duration_seconds=round(time.monotonic() - started, 3),
                        output=output[-10000:],
                        timed_out=True,
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

    @staticmethod
    def _as_text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value
