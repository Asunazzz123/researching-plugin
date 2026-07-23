"""Build a login notification only when subscription candidates remain."""

from __future__ import annotations

from dataclasses import dataclass

from researching_skill_runtime.domain import PaperRecord

from .queue import ResearchQueue


@dataclass(frozen=True, slots=True)
class LoginNotice:
    """User-visible handoff from anonymous discovery to browser authentication."""

    count: int
    papers: tuple[PaperRecord, ...]
    message: str


def build_login_notice(
    queue: ResearchQueue,
    *,
    institution: str | None = None,
) -> LoginNotice | None:
    """Return a login notice, or None when no institutional session is needed."""

    papers = queue.authentication_required
    if not papers:
        return None
    destination = institution.strip() if institution else "学校/CARSI"
    message = (
        "已完成匿名检索、去重和开放获取解析。"
        f"共有 {len(papers)} 篇可能需要通过 {destination} "
        "验证全文权限；"
        "请登录后再进行逐篇权限检查和下载。"
    )
    return LoginNotice(count=len(papers), papers=papers, message=message)
