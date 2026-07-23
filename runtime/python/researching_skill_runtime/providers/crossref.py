"""Crossref public REST metadata adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from researching_skill_runtime.domain import PaperRecord
from researching_skill_runtime.infrastructure import JsonHttpClient, UrllibJsonClient
from researching_skill_runtime.utils import strip_markup


class CrossrefProvider:
    """Search bibliographic metadata through Crossref's public REST API."""

    name = "crossref"
    _WORKS_URL = "https://api.crossref.org/works"

    def __init__(
        self,
        *,
        client: JsonHttpClient | None = None,
        mailto: str | None = None,
        user_agent: str = "researching-plugin/1.0",
    ) -> None:
        self._client = client or UrllibJsonClient()
        self._mailto = mailto.strip() if mailto else None
        self._user_agent = user_agent.strip()
        if not self._user_agent:
            raise ValueError("user_agent must not be empty")

    def search(self, query: str, *, limit: int = 20) -> Sequence[PaperRecord]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")

        params: dict[str, str | int] = {
            "query.bibliographic": normalized_query,
            "rows": limit,
        }
        if self._mailto:
            params["mailto"] = self._mailto
        payload = self._client.get_json(
            self._WORKS_URL,
            params=params,
            headers={"User-Agent": self._user_agent},
        )
        message = payload.get("message")
        if not isinstance(message, Mapping):
            raise ValueError("Crossref response is missing message metadata")
        items = message.get("items", [])
        if not isinstance(items, list):
            raise ValueError("Crossref response contains invalid items")

        records: list[PaperRecord] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            record = _parse_item(item)
            if record is not None:
                records.append(record)
        return tuple(records)


def _parse_item(item: Mapping[str, Any]) -> PaperRecord | None:
    title = strip_markup(_first_text(item.get("title")))
    if not title:
        return None

    authors: list[str] = []
    raw_authors = item.get("author", [])
    if isinstance(raw_authors, list):
        for author in raw_authors:
            if not isinstance(author, Mapping):
                continue
            name = " ".join(
                part.strip()
                for part in (
                    str(author.get("given", "")),
                    str(author.get("family", "")),
                )
                if part.strip()
            )
            if name:
                authors.append(name)

    return PaperRecord(
        title=title,
        authors=tuple(authors),
        year=_publication_year(item),
        venue=_first_text(item.get("container-title")),
        doi=_text(item.get("DOI")),
        abstract=strip_markup(_text(item.get("abstract"))),
        publisher_url=_text(item.get("URL")),
        citation_count=_nonnegative_int(item.get("is-referenced-by-count")),
        reference_count=_nonnegative_int(item.get("references-count")),
        sources=(CrossrefProvider.name,),
    )


def _publication_year(item: Mapping[str, Any]) -> int | None:
    for key in ("published-print", "published-online", "published", "created"):
        value = item.get(key)
        if not isinstance(value, Mapping):
            continue
        date_parts = value.get("date-parts")
        if (
            isinstance(date_parts, list)
            and date_parts
            and isinstance(date_parts[0], list)
            and date_parts[0]
        ):
            year = _nonnegative_int(date_parts[0][0])
            if year:
                return year
    return None


def _first_text(value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return None
    return _text(value[0])


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None
