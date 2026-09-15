"""Guarded autonomous issue-to-PR runner."""

import os
import re
import subprocess
from pathlib import Path
import requests
import json
import time

from .swe_agent import SWEAgent
from .env import SandboxEnv
from .github_client import GitHubClient
from .model import OmniRouteModel
from .planner import IssuePlan, Planner
from .task_state import create_task_state
from .task_state import TaskExecutionState
from .metrics import CycleMetrics
from .reviewer import Reviewer


class AutonomousRunner:
    """Solve issues in isolated branches and publish pull requests."""

    def __init__(self, workspace: str):
        self.workspace = Path(workspace).resolve()
        self.client = GitHubClient(
            os.environ["GITHUB_OWNER"],
            os.environ["GITHUB_REPO"],
            os.environ["GITHUB_TOKEN"],
        )
        self.max_iterations = int(os.getenv("BASTIAO_MAX_ITERATIONS", "20"))
        self.planner = Planner()
        self.state_root = Path(os.getenv("BASTIAO_STATE_DIR", "/var/lib/bastiao"))
        self.state_dir = str(self.state_root / "tasks")
        self.approval_file = Path(
            os.getenv("BASTIAO_APPROVAL_FILE", str(self.state_root / "approvals.json"))
        )
        self.metrics = CycleMetrics(str(self.state_root / "metrics"))
        self.reviewer = Reviewer()

    def _is_approved(self, issue_number: int) -> bool:
        if os.getenv("BASTIAO_REQUIRE_APPROVAL", "true").lower() != "true":
            return True
        try:
            approvals = json.loads(self.approval_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return False
        if not isinstance(approvals, list):
            raise ValueError("approval file must contain a JSON list of issue numbers")
        return issue_number in {int(value) for value in approvals}

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.workspace,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def _changed_files(self) -> list[dict]:
        tracked = self._git("diff", "--name-only", "origin/main").splitlines()
        status = self._git("status", "--short", "--untracked-files=all").splitlines()
        untracked = [
            line[3:]
            for line in status
            if line.startswith("?? ") and line[3:]
        ]
        paths = list(dict.fromkeys(tracked + untracked))
        files = []
        for relative in paths:
            path = Path(relative)
            if not relative or relative.startswith(".env") or ".git" in path.parts:
                continue
            full_path = (self.workspace / path).resolve()
            if self.workspace not in full_path.parents or not full_path.is_file():
                continue
            files.append({"path": relative, "content": full_path.read_text(encoding="utf-8")})
        return files

    def _run_tests(self) -> None:
        """Run repository tests before publishing a patch."""
        tests_dir = self.workspace / "tests"
        if tests_dir.is_dir():
            self._git("status", "--short")
            subprocess.run(
                ["python", "-m", "pytest", "tests", "-q"],
                cwd=self.workspace,
                check=True,
            )
        else:
            subprocess.run(
                ["python", "-m", "compileall", "-q", "."],
                cwd=self.workspace,
                check=True,
            )

    def _has_safe_diff(self) -> bool:
        """Reject accidental wholesale replacements before publishing a PR."""
        result = subprocess.run(
            ["git", "diff", "--numstat", "origin/main"],
            cwd=self.workspace,
            check=True,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            additions, deletions, _ = line.split("\t", 2)
            added = int(additions)
            removed = int(deletions)
            if removed > 40 and removed > max(added * 5, 100):
                return False
        subprocess.run(
            ["git", "diff", "--check", "origin/main"],
            cwd=self.workspace,
            check=True,
        )
        return True

    @staticmethod
    def _format_plan(plan) -> str:
        """Provide the model with the complete planner contract."""
        criteria = "\n".join(f"- {item}" for item in plan.acceptance_criteria) or "- none"
        paths = "\n".join(f"- {path}" for path in plan.allowed_paths) or "- none explicitly named"
        steps = "\n".join(
            f"- {step.id}: {step.title} ({step.action})" for step in plan.steps
        )
        return f"""Allowed paths:
{paths}

Acceptance criteria:
{criteria}

Steps:
{steps}"""

    def _issue_paths(self, title: str, body: str) -> set[str]:
        """Extract explicit repository paths from an issue for scope validation."""
        text = f"{title}\n{body}"
        candidates = set(re.findall(r"`([^`]+)`", text))
        candidates.update(
            re.findall(
                r"\b(?:src|tests|scripts|docs|utils|open-sse)(?:/[A-Za-z0-9_.-]+)+",
                text,
            )
        )
        paths = set()
        for candidate in candidates:
            normalized = candidate.strip().replace("\\", "/").lstrip("./")
            if (
                "/" in normalized
                and not normalized.startswith(("http://", "https://"))
                and not normalized.endswith("/")
            ):
                paths.add(normalized)
        return paths

    def _has_in_scope_diff(self, title: str, body: str, files: list[dict]) -> bool:
        """Reject patches that do not touch the issue's explicit target files."""
        issue_paths = self._issue_paths(title, body)
        changed = {file["path"].replace("\\", "/") for file in files}
        if not changed:
            return False
        if issue_paths and not changed.issubset(issue_paths):
            return False
        if issue_paths and not changed.intersection(issue_paths):
            return False
        if not issue_paths:
            issue_text = f"{title}\n{body}".lower()
            for path in changed:
                existing = (self.workspace / path).exists()
                if existing and path.lower() not in issue_text and Path(path).name.lower() not in issue_text:
                    return False
        return True

    def run_once(self) -> dict:
        started = time.monotonic()
        result = self._run_once()
        self.metrics.record(result, time.monotonic() - started)
        return result

    def _run_once(self) -> dict:
        try:
            issues = self.client.list_issues(state="open")
        except requests.RequestException as error:
            return {
                "status": "github_unavailable",
                "error": f"{type(error).__name__}: {error}",
            }
        processed = 0
        retry = os.getenv("BASTIAO_RETRY_ISSUES", "false").lower() == "true"
        selected_numbers = {
            int(value.strip())
            for value in os.getenv("BASTIAO_ISSUE_NUMBERS", "").split(",")
            if value.strip().isdigit()
        }
        skipped = set()
        for issue in issues:
            if selected_numbers and issue.number not in selected_numbers:
                continue
            branch = f"bastiao/issue-{issue.number}"
            if not retry:
                try:
                    if self.client.has_pull_request_for_branch(branch):
                        skipped.add(issue.number)
                        continue
                except requests.RequestException as error:
                    return {
                        "issue": issue.number,
                        "status": "github_unavailable",
                        "error": f"{type(error).__name__}: {error}",
                    }
            if processed >= int(os.getenv("BASTIAO_MAX_ISSUES", "1")):
                break
            if not self._is_approved(issue.number):
                skipped.add(issue.number)
                return {"issue": issue.number, "status": "pending_approval"}
            processed += 1
            self._git("fetch", "origin", "main")
            state_path = self.state_root / "tasks" / f"issue-{issue.number}.json"
            state = None
            if state_path.exists():
                state = TaskExecutionState.load(str(state_path))
            if state and state.status in {"failed", "running"} and state.branch == branch:
                self._git("checkout", branch)
                plan = IssuePlan.from_dict(state.plan)
            else:
                self._git("checkout", "-B", branch, "origin/main")
                plan = self.planner.build_issue_plan(issue)
                state = create_task_state(plan)
                state.branch = branch
            if state is None:
                state = create_task_state(plan)
                state.branch = branch
            self.client.create_branch(branch)
            state.start_step()
            state.save(self.state_dir)

            agent = SWEAgent(
                model=OmniRouteModel(),
                env=SandboxEnv(str(self.workspace), allowed_paths=plan.allowed_paths),
                max_iterations=self.max_iterations,
            )
            solved = agent.solve(
                issue.title,
                issue.body or "",
                plan=(
                    self._format_plan(plan)
                    + f"\n\nResume checkpoint: step {state.current_step}, "
                    f"attempt {state.attempts}. Last result: {state.result or 'none'}. "
                    f"Previous error: {state.error or 'none'}."
                ),
            )
            files = self._changed_files() if solved else []
            if not solved or not files:
                state.fail("agent did not produce a patch")
                state.save(self.state_dir)
                self.client.add_comment(issue.number, "Bastiao could not produce a tested patch.")
                return {"issue": issue.number, "status": "failed", "files": 0}

            in_scope = self._has_in_scope_diff(issue.title, issue.body or "", files)
            if not in_scope:
                state.fail("patch is outside issue scope")
                state.save(self.state_dir)
                self.client.add_comment(
                    issue.number,
                    "Bastiao rejected the patch because it modified files outside the explicit scope of the issue.",
                )
                return {"issue": issue.number, "status": "rejected_out_of_scope", "files": len(files)}

            self._run_tests()
            state.complete_step()
            state.save(self.state_dir)
            safe_diff = self._has_safe_diff()
            review = self.reviewer.review(
                files,
                in_scope,
                safe_diff,
                issue_text=f"{issue.title}\n{issue.body or ''}",
                workspace=str(self.workspace),
            )
            if not review.approved:
                state.fail("; ".join(review.reasons))
                state.save(self.state_dir)
                self.client.add_comment(
                    issue.number,
                    "Bastiao rejected the patch during review: "
                    + "; ".join(review.reasons)
                    + ". The next approved cycle can resume from the saved branch and checkpoint.",
                )
                return {"issue": issue.number, "status": "rejected_by_reviewer", "reasons": review.reasons}
            if not safe_diff:
                state.fail("unsafe diff")
                state.save(self.state_dir)
                self.client.add_comment(
                    issue.number,
                    "Bastiao rejected the generated patch because it replaced too much existing code.",
                )
                return {"issue": issue.number, "status": "rejected_unsafe_diff", "files": len(files)}
            self.client.commit_files(
                files,
                f"feat: implement #{issue.number} {issue.title}",
                branch=branch,
            )
            pr_url = self.client.create_pull_request(
                branch,
                f"Bastiao: {issue.title}",
                f"Automated implementation for #{issue.number}.\n\n"
                "Tests were executed in the isolated workspace before opening this PR.",
            )
            self.client.add_comment(issue.number, f"Implemented in PR: {pr_url}")
            state.complete()
            state.save(self.state_dir)
            return {"issue": issue.number, "status": "pull_request_opened", "files": len(files), "pr": pr_url}
        return {"status": "no_open_issues", "skipped": sorted(skipped)}
