"""Deterministic pre-publication review gate."""

from dataclasses import dataclass


@dataclass
class ReviewResult:
    approved: bool
    reasons: list[str]


class Reviewer:
    """Reviews a candidate patch independently from the model."""

    def review(self, files: list[dict], in_scope: bool, safe_diff: bool) -> ReviewResult:
        reasons = []
        if not files:
            reasons.append("no files changed")
        if not in_scope:
            reasons.append("patch is outside issue scope")
        if not safe_diff:
            reasons.append("diff failed safety checks")
        return ReviewResult(approved=not reasons, reasons=reasons)
