"""Download-manifest statistics produced before browser authentication."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .queue import ResearchQueue


@dataclass(frozen=True, slots=True)
class DownloadManifest:
    """Stable counts for presenting the anonymous discovery result."""

    total: int
    with_abstract: int
    open_access: int
    authentication_required: int
    unresolved: int
    metadata_only: int

    @classmethod
    def from_queue(cls, queue: ResearchQueue) -> DownloadManifest:
        return cls(
            total=len(queue.papers),
            with_abstract=sum(bool(paper.abstract) for paper in queue.papers),
            open_access=len(queue.open_access),
            authentication_required=len(queue.authentication_required),
            unresolved=len(queue.unresolved),
            metadata_only=len(queue.metadata_only),
        )

    def as_dict(self) -> dict[str, int]:
        return asdict(self)

    def render_text(self) -> str:
        """Render a compact Chinese summary suitable for a Codex response."""

        return "\n".join(
            (
                f"检索并去重：{self.total} 篇",
                f"包含摘要：{self.with_abstract} 篇",
                f"开放全文可下载：{self.open_access} 篇",
                f"需要机构登录：{self.authentication_required} 篇",
                f"全文位置未解析：{self.unresolved} 篇",
                f"尚待访问判定：{self.metadata_only} 篇",
            )
        )
