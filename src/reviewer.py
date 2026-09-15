"""Deterministic pre-publication review gate."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReviewResult:
    approved: bool
    reasons: list[str]


class Reviewer:
    """Reviews a candidate patch independently from the model."""

    def review(
        self,
        files: list[dict],
        in_scope: bool,
        safe_diff: bool,
        issue_text: str = "",
        workspace: str | None = None,
    ) -> ReviewResult:
        reasons = []
        if not files:
            reasons.append("no files changed")
        if not in_scope:
            reasons.append("patch is outside issue scope")
        if not safe_diff:
            reasons.append("diff failed safety checks")
        if workspace and issue_text:
            reasons.extend(self._validate_explicit_content(issue_text, workspace))
        return ReviewResult(approved=not reasons, reasons=reasons)

    def _validate_explicit_content(self, issue_text: str, workspace: str) -> list[str]:
        """Validate simple explicit constant requirements before publication."""
        match = re.search(
            r"(?:constant|constante)\s+`?([A-Za-z_]\w*)`?\s*=\s*([^\s.`]+|\"[^\"]*\"|'[^']*')",
            issue_text,
            re.IGNORECASE,
        )
        if not match:
            return []
        name, expected = match.groups()
        for path in re.findall(r"`([^`]+\.[A-Za-z0-9]+)`", issue_text):
            candidate = Path(workspace) / path
            if not candidate.is_file():
                continue
            content = candidate.read_text(encoding="utf-8")
            if candidate.suffix == ".py":
                try:
                    compile(content, str(candidate), "exec")
                except SyntaxError:
                    return [f"invalid Python syntax in {path}"]
            assignment = re.search(
                rf"^\s*{re.escape(name)}\s*=\s*(.+?)\s*$", content, re.MULTILINE
            )
            if not assignment:
                return [f"missing required constant {name}"]
            actual = assignment.group(1).strip()
            if actual != expected:
                return [f"constant {name} does not match issue requirement"]
        return []
