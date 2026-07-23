"""Metadata-provider contracts."""

from __future__ import annotations

from typing import Protocol, Sequence

from researching_skill_runtime.domain import PaperRecord


class MetadataProvider(Protocol):
    """Search a public scholarly index and return canonical records."""

    @property
    def name(self) -> str:
        """Return the stable provider identifier."""

        ...

    def search(self, query: str, *, limit: int = 20) -> Sequence[PaperRecord]:
        """Search provider metadata without institutional authentication."""

        ...
