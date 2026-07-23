"""Access-resolution contracts."""

from __future__ import annotations

from typing import Protocol

from researching_skill_runtime.domain import PaperRecord


class AccessResolver(Protocol):
    """Enrich a paper with its best known legal full-text access state."""

    @property
    def name(self) -> str:
        """Return the stable resolver identifier."""

        ...

    def resolve(self, paper: PaperRecord) -> PaperRecord:
        """Resolve open access or mark a likely institutional-login boundary."""

        ...
