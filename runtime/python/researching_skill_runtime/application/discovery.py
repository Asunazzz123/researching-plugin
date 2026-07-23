"""Public metadata discovery, deduplication, and access resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from researching_skill_runtime.domain import PaperRecord
from researching_skill_runtime.providers import MetadataProvider
from researching_skill_runtime.resolvers import AccessResolver
from researching_skill_runtime.utils import normalize_title, redact_secrets

from .manifest import DownloadManifest
from .queue import ResearchQueue


@dataclass(frozen=True, slots=True)
class DiscoveryIssue:
    """Non-fatal provider or resolver failure retained for diagnostics."""

    component: str
    operation: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Anonymous discovery output ready for display or authentication gating."""

    queue: ResearchQueue
    manifest: DownloadManifest
    issues: tuple[DiscoveryIssue, ...] = ()


class DiscoveryService:
    """Orchestrate public indexes without requiring an institutional login."""

    def __init__(
        self,
        providers: Sequence[MetadataProvider],
        *,
        resolvers: Sequence[AccessResolver] = (),
    ) -> None:
        if not providers:
            raise ValueError("at least one metadata provider is required")
        self._providers = tuple(providers)
        self._resolvers = tuple(resolvers)

    def discover(self, query: str, *, limit_per_provider: int = 20) -> DiscoveryResult:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")
        if limit_per_provider <= 0:
            raise ValueError("limit_per_provider must be positive")

        records: list[PaperRecord] = []
        issues: list[DiscoveryIssue] = []
        for provider in self._providers:
            try:
                records.extend(
                    provider.search(normalized_query, limit=limit_per_provider)
                )
            except Exception as exc:
                issues.append(_issue(provider.name, "search", exc))

        papers = _deduplicate(records)
        resolved: list[PaperRecord] = []
        for paper in papers:
            current = paper
            for resolver in self._resolvers:
                try:
                    current = resolver.resolve(current)
                except Exception as exc:
                    issues.append(_issue(resolver.name, "resolve", exc))
            resolved.append(current)

        queue = ResearchQueue.from_papers(resolved)
        return DiscoveryResult(
            queue=queue,
            manifest=DownloadManifest.from_queue(queue),
            issues=tuple(issues),
        )


def _deduplicate(records: Iterable[PaperRecord]) -> tuple[PaperRecord, ...]:
    papers: list[PaperRecord] = []
    doi_index: dict[str, int] = {}
    title_index: dict[str, list[int]] = {}

    for record in records:
        title_key = normalize_title(record.title)
        index = doi_index.get(record.doi) if record.doi else None
        if index is None:
            candidates = [
                candidate
                for candidate in title_index.get(title_key, [])
                if papers[candidate].matches(record)
            ]
            if len(candidates) == 1:
                index = candidates[0]

        if index is None:
            index = len(papers)
            papers.append(record)
            title_index.setdefault(title_key, []).append(index)
        else:
            papers[index] = papers[index].merge(record)

        merged = papers[index]
        if merged.doi:
            doi_index[merged.doi] = index
        merged_title_key = normalize_title(merged.title)
        candidates = title_index.setdefault(merged_title_key, [])
        if index not in candidates:
            candidates.append(index)

    return tuple(papers)


def _issue(component: str, operation: str, exc: Exception) -> DiscoveryIssue:
    return DiscoveryIssue(
        component=component,
        operation=operation,
        error_type=type(exc).__name__,
        message=redact_secrets(str(exc)),
    )
