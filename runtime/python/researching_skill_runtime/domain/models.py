"""Canonical paper metadata and access-state models."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from researching_skill_runtime.utils.identifiers import normalize_doi
from researching_skill_runtime.utils.text import clean_text, normalize_title


class AccessStatus(StrEnum):
    """Best known full-text access state without overstating entitlement."""

    METADATA_ONLY = "metadata_only"
    OPEN_ACCESS = "open_access"
    AUTHENTICATION_REQUIRED = "authentication_required"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class PaperRecord:
    """Normalized metadata assembled from one or more public sources."""

    title: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    abstract: str | None = None
    publisher_url: str | None = None
    open_access_url: str | None = None
    citation_count: int | None = None
    reference_count: int | None = None
    sources: tuple[str, ...] = ()
    access_status: AccessStatus = AccessStatus.METADATA_ONLY

    def __post_init__(self) -> None:
        try:
            access_status = AccessStatus(self.access_status)
        except ValueError as exc:
            message = f"unsupported access status: {self.access_status!r}"
            raise ValueError(message) from exc
        title = clean_text(self.title)
        if not title:
            raise ValueError("paper title must not be empty")
        if self.year is not None and self.year <= 0:
            raise ValueError("paper year must be positive")
        if self.citation_count is not None and self.citation_count < 0:
            raise ValueError("citation_count must not be negative")
        if self.reference_count is not None and self.reference_count < 0:
            raise ValueError("reference_count must not be negative")

        object.__setattr__(self, "title", title)
        object.__setattr__(self, "access_status", access_status)
        object.__setattr__(
            self,
            "authors",
            _unique_nonempty(self.authors),
        )
        object.__setattr__(self, "venue", _optional_text(self.venue))
        object.__setattr__(self, "doi", normalize_doi(self.doi))
        object.__setattr__(self, "abstract", _optional_text(self.abstract))
        object.__setattr__(
            self,
            "publisher_url",
            _optional_text(self.publisher_url),
        )
        object.__setattr__(
            self,
            "open_access_url",
            _optional_text(self.open_access_url),
        )
        object.__setattr__(self, "sources", _unique_nonempty(self.sources))

        if self.open_access_url and self.access_status is AccessStatus.METADATA_ONLY:
            object.__setattr__(self, "access_status", AccessStatus.OPEN_ACCESS)

    @property
    def deduplication_key(self) -> str:
        """Return a stable DOI key, with a conservative title/year fallback."""

        if self.doi:
            return f"doi:{self.doi}"
        year = str(self.year) if self.year is not None else "unknown"
        return f"title:{normalize_title(self.title)}:{year}"

    def matches(self, other: PaperRecord) -> bool:
        """Report whether two records conservatively identify the same work."""

        if self.doi and other.doi:
            return self.doi == other.doi
        if normalize_title(self.title) != normalize_title(other.title):
            return False
        return self.year is None or other.year is None or self.year == other.year

    def merge(self, other: PaperRecord) -> PaperRecord:
        """Merge duplicate records while preferring richer non-empty values."""

        if not self.matches(other):
            raise ValueError("only records identifying the same paper can merge")

        access_status = _richer_access_status(
            self.access_status,
            other.access_status,
        )
        return PaperRecord(
            title=_prefer_longer(self.title, other.title) or self.title,
            authors=_merge_unique(self.authors, other.authors),
            year=self.year or other.year,
            venue=_prefer_longer(self.venue, other.venue),
            doi=self.doi or other.doi,
            abstract=_prefer_longer(self.abstract, other.abstract),
            publisher_url=self.publisher_url or other.publisher_url,
            open_access_url=self.open_access_url or other.open_access_url,
            citation_count=_prefer_count(self.citation_count, other.citation_count),
            reference_count=_prefer_count(
                self.reference_count,
                other.reference_count,
            ),
            sources=_merge_unique(self.sources, other.sources),
            access_status=access_status,
        )

    def with_access(
        self,
        status: AccessStatus,
        *,
        open_access_url: str | None = None,
    ) -> PaperRecord:
        """Return a copy with a resolved access state."""

        return replace(
            self,
            access_status=status,
            open_access_url=open_access_url or self.open_access_url,
        )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return clean_text(value) or None


def _unique_nonempty(values: tuple[str, ...]) -> tuple[str, ...]:
    return _merge_unique((), values)


def _merge_unique(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in (*left, *right):
        normalized = clean_text(value)
        key = normalized.casefold()
        if normalized and key not in seen:
            result.append(normalized)
            seen.add(key)
    return tuple(result)


def _prefer_longer(left: str | None, right: str | None) -> str | None:
    candidates = [value for value in (left, right) if value]
    return max(candidates, key=len) if candidates else None


def _prefer_count(left: int | None, right: int | None) -> int | None:
    values = [value for value in (left, right) if value is not None]
    return max(values) if values else None


def _richer_access_status(
    left: AccessStatus,
    right: AccessStatus,
) -> AccessStatus:
    priority = {
        AccessStatus.METADATA_ONLY: 0,
        AccessStatus.UNRESOLVED: 1,
        AccessStatus.AUTHENTICATION_REQUIRED: 2,
        AccessStatus.OPEN_ACCESS: 3,
    }
    return left if priority[left] >= priority[right] else right
