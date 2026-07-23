"""Immutable research queue partitioned by access boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from researching_skill_runtime.domain import AccessStatus, PaperRecord


@dataclass(frozen=True, slots=True)
class ResearchQueue:
    """Canonical papers awaiting OA download, login, or manual resolution."""

    papers: tuple[PaperRecord, ...]

    @classmethod
    def from_papers(cls, papers: Iterable[PaperRecord]) -> ResearchQueue:
        return cls(tuple(papers))

    @property
    def open_access(self) -> tuple[PaperRecord, ...]:
        return self._with_status(AccessStatus.OPEN_ACCESS)

    @property
    def authentication_required(self) -> tuple[PaperRecord, ...]:
        return self._with_status(AccessStatus.AUTHENTICATION_REQUIRED)

    @property
    def unresolved(self) -> tuple[PaperRecord, ...]:
        return self._with_status(AccessStatus.UNRESOLVED)

    @property
    def metadata_only(self) -> tuple[PaperRecord, ...]:
        return self._with_status(AccessStatus.METADATA_ONLY)

    @property
    def needs_authentication(self) -> bool:
        return bool(self.authentication_required)

    def _with_status(self, status: AccessStatus) -> tuple[PaperRecord, ...]:
        return tuple(paper for paper in self.papers if paper.access_status is status)
