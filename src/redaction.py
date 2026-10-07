"""Secret redaction for logs, metrics and any text that leaves the process."""

import logging
import os
import re

REDACTED = "[REDACTED]"

_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)(authorization\s*[:=]\s*)(?:bearer|token|basic)?\s*[^\s,;'\"]+"),
    re.compile(r"(?i)((?:token|password|secret|api[_-]?key)\s*[=:]\s*)[^\s,;'\"]+"),
]
_SECRET_ENV_NAMES = ("GITHUB_TOKEN", "OMNIROUTE_API_KEY")


def redact(text: str) -> str:
    """Mask known token formats and the configured secret values."""
    for name in _SECRET_ENV_NAMES:
        value = os.getenv(name, "")
        if len(value) >= 8:
            text = text.replace(value, REDACTED)
    for pattern in _PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda match: match.group(1) + REDACTED, text)
        else:
            text = pattern.sub(REDACTED, text)
    return text


def redact_data(value):
    """Redact every string inside nested dicts and lists."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {key: redact_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_data(item) for item in value]
    return value


class RedactingFilter(logging.Filter):
    """Logging filter that masks secrets in the formatted message."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def install_log_redaction() -> None:
    """Attach the filter to every root handler so all loggers are covered."""
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(item, RedactingFilter) for item in handler.filters):
            handler.addFilter(RedactingFilter())
