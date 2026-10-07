"""Bounded subprocess execution: process-tree kill, optional rlimits, scrubbed env."""

from dataclasses import dataclass
import os
import signal
import subprocess
import sys
from typing import Optional

SECRET_ENV_NAMES = {"GITHUB_TOKEN", "OMNIROUTE_API_KEY"}
SECRET_ENV_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY")


@dataclass(frozen=True)
class ProcessResult:
    returncode: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool = False


def sanitized_env(extra: Optional[dict] = None) -> dict:
    """Environment for model-driven commands, without credentials."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in SECRET_ENV_NAMES
        and not any(marker in key.upper() for marker in SECRET_ENV_MARKERS)
    }
    env.update(extra or {})
    return env


def _limits_preexec(memory_mb: int, cpu_seconds: int):
    """Build a POSIX-only preexec hook that applies address-space and CPU limits."""

    def apply() -> None:
        import resource

        if memory_mb > 0:
            limit = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        if cpu_seconds > 0:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

    return apply


def kill_tree(process: subprocess.Popen) -> None:
    """Terminate the process and all its descendants."""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    process.kill()


def run_bounded(
    argv: list[str],
    cwd: str,
    timeout: float,
    env: Optional[dict] = None,
    memory_mb: int = 0,
    cpu_seconds: int = 0,
) -> ProcessResult:
    """Run argv with a timeout that also kills child processes it spawned."""
    options: dict = {}
    if sys.platform == "win32":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
        if memory_mb > 0 or cpu_seconds > 0:
            options["preexec_fn"] = _limits_preexec(memory_mb, cpu_seconds)

    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **options,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return ProcessResult(process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        kill_tree(process)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        return ProcessResult(None, stdout or "", stderr or "", timed_out=True)
