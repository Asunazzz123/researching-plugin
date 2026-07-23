"""Pure redaction helpers for safe diagnostics."""

from __future__ import annotations

import re

_QUERY_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|authorization|email|mailto)=([^&\s]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;]+")


def redact_secrets(value: str) -> str:
    """Redact common API credentials from provider exception messages."""

    redacted = _QUERY_SECRET_PATTERN.sub(r"\1=[REDACTED]", value)
    return _BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
