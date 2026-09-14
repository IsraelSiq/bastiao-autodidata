"""Guarded autonomous issue-to-PR runner."""

import os
import re
import subprocess
from pathlib import Path

from .swe_agent import SWEAgent
from .env import SandboxEnv
from .github_client import GitHubClient
from .model import OmniRouteModel
from .planner import Planner
from .task_state import create_task_state


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
        self.state_dir = os.getenv("BASTIAO_STATE_DIR", str(self.workspace / ".bastiao" / "tasks"))

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
        paths = self._git("diff", "--name-only", "origin/main").splitlines()
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
        issues = self.client.list_issues(state="open")
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
            if not retry and self.client.has_pull_request_for_branch(branch):
                skipped.add(issue.number)
                continue
            if processed >= int(os.getenv("BASTIAO_MAX_ISSUES", "1")):
                break
            processed += 1
            self._git("fetch", "origin", "main")
            self._git("checkout", "-B", branch, "origin/main")
            self.client.create_branch(branch)
            plan = self.planner.build_issue_plan(issue)
            state = create_task_state(plan)
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
                plan="\n".join(
                    f"{step.id}: {step.title} ({step.action})" for step in plan.steps
                ),
            )
            files = self._changed_files() if solved else []
            if not solved or not files:
                state.fail("agent did not produce a patch")
                state.save(self.state_dir)
                self.client.add_comment(issue.number, "Bastiao could not produce a tested patch.")
                return {"issue": issue.number, "status": "failed", "files": 0}

            if not self._has_in_scope_diff(issue.title, issue.body or "", files):
                state.fail("patch is outside issue scope")
                state.save(self.state_dir)
                self.client.add_comment(
                    issue.number,
                    "Bastiao rejected the patch because it modified files outside the explicit scope of the issue.",
                )
                return {"issue": issue.number, "status": "rejected_out_of_scope", "files": len(files)}

            self._run_tests()
            state.complete_step()
            state.complete()
            state.save(self.state_dir)
            if not self._has_safe_diff():
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
