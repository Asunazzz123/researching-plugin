"""Unpaywall open-access location resolver."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from researching_skill_runtime.domain import AccessStatus, PaperRecord
from researching_skill_runtime.infrastructure import JsonHttpClient, UrllibJsonClient


class UnpaywallResolver:
    """Resolve a DOI to a legal OA copy before requesting library login."""

    name = "unpaywall"
    _BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(
        self,
        email: str,
        *,
        client: JsonHttpClient | None = None,
    ) -> None:
        self._email = email.strip()
        if "@" not in self._email:
            raise ValueError("Unpaywall requires a contact email")
        self._client = client or UrllibJsonClient()

    def resolve(self, paper: PaperRecord) -> PaperRecord:
        if paper.open_access_url:
            return paper.with_access(AccessStatus.OPEN_ACCESS)
        if not paper.doi:
            return paper.with_access(AccessStatus.UNRESOLVED)

        payload = self._client.get_json(
            f"{self._BASE_URL}/{quote(paper.doi, safe='/')}",
            params={"email": self._email},
        )
        location = payload.get("best_oa_location")
        if isinstance(location, Mapping):
            oa_url = _text(location.get("url_for_pdf")) or _text(
                location.get("url")
            )
            if oa_url:
                return paper.with_access(
                    AccessStatus.OPEN_ACCESS,
                    open_access_url=oa_url,
                )

        is_oa = payload.get("is_oa")
        if is_oa is False:
            return paper.with_access(AccessStatus.AUTHENTICATION_REQUIRED)
        return paper.with_access(AccessStatus.UNRESOLVED)


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
