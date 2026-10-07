"""Read-only dependency healthchecks for GitHub, Ollama, workspace and ChromaDB."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import time

import requests


@dataclass(frozen=True)
class HealthCheck:
    """Outcome of one dependency probe."""

    name: str
    ok: bool
    detail: str
    duration_seconds: float
    required: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "required": self.required,
            "detail": self.detail,
            "duration_seconds": self.duration_seconds,
        }


def _probe(name: str, required: bool, func) -> HealthCheck:
    started = time.monotonic()
    try:
        ok, detail = func()
    except requests.RequestException as error:
        ok, detail = False, type(error).__name__
    except OSError as error:
        ok, detail = False, f"{type(error).__name__}: {error}"
    return HealthCheck(
        name=name,
        ok=ok,
        detail=detail,
        duration_seconds=round(time.monotonic() - started, 3),
        required=required,
    )


def check_github(timeout: float) -> HealthCheck:
    """Verify the token can read the target repository; the token is never reported."""

    def run():
        owner = os.getenv("GITHUB_OWNER")
        repo = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        if not (owner and repo and token):
            return False, "missing GITHUB_OWNER, GITHUB_REPO or GITHUB_TOKEN"
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"Authorization": f"token {token}"},
            timeout=timeout,
        )
        return response.ok, f"HTTP {response.status_code}"

    return _probe("github", True, run)


def check_ollama(timeout: float) -> HealthCheck:
    """Verify the OpenAI-compatible endpoint lists models."""

    def run():
        base = os.getenv("OMNIROUTE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
        url = f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
        response = requests.get(url, timeout=timeout)
        return response.ok, f"HTTP {response.status_code}"

    return _probe("ollama", True, run)


def check_workspace() -> HealthCheck:
    """Verify the workspace is an existing Git checkout."""

    def run():
        workspace = os.getenv("BASTIAO_WORKSPACE")
        if not workspace:
            return False, "BASTIAO_WORKSPACE is not set"
        path = Path(workspace)
        if not path.is_dir():
            return False, "workspace directory not found"
        if not (path / ".git").exists():
            return False, "workspace is not a git checkout"
        return True, "git checkout present"

    return _probe("workspace", True, run)


def check_chroma(timeout: float) -> HealthCheck:
    """Probe ChromaDB; optional because the current issue-to-PR flow does not use it."""

    def run():
        base = os.getenv("CHROMA_URL", "http://127.0.0.1:8000").rstrip("/")
        response = requests.get(f"{base}/api/v2/heartbeat", timeout=timeout)
        if response.status_code == 404:
            response = requests.get(f"{base}/api/v1/heartbeat", timeout=timeout)
        return response.ok, f"HTTP {response.status_code}"

    return _probe("chroma", False, run)


def collect_health(timeout: float | None = None) -> dict:
    """Run every probe once; only required checks decide the overall result."""
    timeout = timeout or float(os.getenv("BASTIAO_HEALTH_TIMEOUT_SECONDS", "5"))
    checks = [
        check_github(timeout),
        check_ollama(timeout),
        check_workspace(),
        check_chroma(timeout),
    ]
    return {
        "ok": all(check.ok for check in checks if check.required),
        "checks": [check.to_dict() for check in checks],
    }


def main() -> int:
    report = collect_health()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
