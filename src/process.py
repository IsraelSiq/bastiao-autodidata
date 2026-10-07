"""Bounded subprocess execution: process-tree kill, optional rlimits, scrubbed env."""

from dataclasses import dataclass
import os
import signal
import subprocess
import sys
import threading
from typing import BinaryIO, Optional

SECRET_ENV_NAMES = {"GITHUB_TOKEN", "OMNIROUTE_API_KEY"}
SECRET_ENV_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY")


@dataclass(frozen=True)
class ProcessResult:
    returncode: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool = False
    output_truncated: bool = False
    limit_exceeded: Optional[str] = None


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
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))

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
    if process.poll() is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass


def _drain_stream(
    stream: BinaryIO,
    max_output_bytes: int,
    result: list[tuple[bytes, bool]],
    errors: list[OSError],
) -> None:
    output = bytearray()
    truncated = False
    try:
        while chunk := stream.read(65536):
            remaining = max_output_bytes - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated = True
    except OSError as error:
        errors.append(error)
    result.append((bytes(output), truncated))


def run_bounded(
    argv: list[str],
    cwd: str,
    timeout: float,
    env: Optional[dict] = None,
    memory_mb: int = 0,
    cpu_seconds: int = 0,
    max_output_bytes: int = 1_000_000,
) -> ProcessResult:
    """Run argv with bounded output and a timeout that kills its child processes."""
    if max_output_bytes < 0:
        raise ValueError("max_output_bytes must be non-negative")
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
        **options,
    )
    stdout_result: list[tuple[bytes, bool]] = []
    stderr_result: list[tuple[bytes, bool]] = []
    reader_errors: list[OSError] = []
    readers = [
        threading.Thread(
            target=_drain_stream,
            args=(process.stdout, max_output_bytes, stdout_result, reader_errors),
            daemon=True,
        ),
        threading.Thread(
            target=_drain_stream,
            args=(process.stderr, max_output_bytes, stderr_result, reader_errors),
            daemon=True,
        ),
    ]
    for reader in readers:
        reader.start()

    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(process)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    for reader in readers:
        reader.join(timeout=5)
    if any(reader.is_alive() for reader in readers):
        kill_tree(process)
        for reader in readers:
            reader.join(timeout=5)
        if any(reader.is_alive() for reader in readers):
            raise RuntimeError("Could not finish reading subprocess output")
    if reader_errors:
        raise reader_errors[0]

    stdout_bytes, stdout_truncated = stdout_result[0]
    stderr_bytes, stderr_truncated = stderr_result[0]
    return ProcessResult(
        None if timed_out else process.returncode,
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
        timed_out=timed_out,
        output_truncated=stdout_truncated or stderr_truncated,
        limit_exceeded=(
            "memory"
            if memory_mb > 0 and b"MemoryError" in stderr_bytes
            else (
                "cpu"
                if cpu_seconds > 0
                and process.returncode == -getattr(signal, "SIGXCPU", -999)
                else None
            )
        ),
    )
