"""Small, deterministic text-normalization helpers."""

from __future__ import annotations

import html
import re
import unicodedata

_TAG_PATTERN = re.compile(r"<[^>]+>")
_NON_WORD_PATTERN = re.compile(r"[^\w]+", re.UNICODE)


def clean_text(value: str) -> str:
    """Decode entities and collapse Unicode whitespace."""

    decoded = html.unescape(value)
    return " ".join(decoded.split())


def strip_markup(value: str | None) -> str | None:
    """Remove simple JATS/HTML tags from provider-supplied metadata."""

    if value is None:
        return None
    stripped = clean_text(_TAG_PATTERN.sub(" ", value))
    return stripped or None


def normalize_title(value: str) -> str:
    """Create a conservative title key for DOI-less deduplication."""

    normalized = unicodedata.normalize("NFKC", clean_text(value)).casefold()
    return _NON_WORD_PATTERN.sub(" ", normalized).strip()
