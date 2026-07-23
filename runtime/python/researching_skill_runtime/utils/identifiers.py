"""Persistent-identifier normalization."""

from __future__ import annotations

from urllib.parse import unquote


def normalize_doi(value: str | None) -> str | None:
    """Normalize a DOI or DOI URL to its lowercase registrant form."""

    if value is None:
        return None
    normalized = unquote(value).strip()
    if not normalized:
        return None

    lowered = normalized.casefold()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if lowered.startswith(prefix):
            normalized = normalized[len(prefix) :].strip()
            break
    normalized = normalized.rstrip(". ,;")
    if not normalized.casefold().startswith("10.") or "/" not in normalized:
        return None
    return normalized.casefold()
