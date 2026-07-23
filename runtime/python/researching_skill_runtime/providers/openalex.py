"""OpenAlex scholarly-graph metadata adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from researching_skill_runtime.domain import AccessStatus, PaperRecord
from researching_skill_runtime.infrastructure import JsonHttpClient, UrllibJsonClient


class OpenAlexProvider:
    """Search OpenAlex with a free service API key, not a library login."""

    name = "openalex"
    _WORKS_URL = "https://api.openalex.org/works"

    def __init__(
        self,
        api_key: str,
        *,
        client: JsonHttpClient | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        if not self._api_key:
            raise ValueError("OpenAlex api_key must not be empty")
        self._client = client or UrllibJsonClient()

    def search(self, query: str, *, limit: int = 20) -> Sequence[PaperRecord]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        payload = self._client.get_json(
            self._WORKS_URL,
            params={
                "search": normalized_query,
                "per-page": limit,
                "api_key": self._api_key,
            },
        )
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ValueError("OpenAlex response contains invalid results")

        records: list[PaperRecord] = []
        for item in results:
            if not isinstance(item, Mapping):
                continue
            record = _parse_work(item)
            if record is not None:
                records.append(record)
        return tuple(records)


def _parse_work(item: Mapping[str, Any]) -> PaperRecord | None:
    title = _text(item.get("display_name")) or _text(item.get("title"))
    if not title:
        return None

    authors: list[str] = []
    authorships = item.get("authorships", [])
    if isinstance(authorships, list):
        for authorship in authorships:
            if not isinstance(authorship, Mapping):
                continue
            author = authorship.get("author")
            if isinstance(author, Mapping):
                name = _text(author.get("display_name"))
                if name:
                    authors.append(name)

    primary_location = item.get("primary_location")
    location = primary_location if isinstance(primary_location, Mapping) else {}
    source = location.get("source")
    venue = _text(source.get("display_name")) if isinstance(source, Mapping) else None

    best_oa_location = item.get("best_oa_location")
    oa_location = (
        best_oa_location if isinstance(best_oa_location, Mapping) else {}
    )
    oa_url = _text(oa_location.get("pdf_url")) or _text(
        oa_location.get("landing_page_url")
    )
    access_status = (
        AccessStatus.OPEN_ACCESS if oa_url else AccessStatus.METADATA_ONLY
    )

    return PaperRecord(
        title=title,
        authors=tuple(authors),
        year=_positive_int(item.get("publication_year")),
        venue=venue,
        doi=_text(item.get("doi")),
        abstract=_reconstruct_abstract(item.get("abstract_inverted_index")),
        publisher_url=_text(location.get("landing_page_url")),
        open_access_url=oa_url,
        citation_count=_nonnegative_int(item.get("cited_by_count")),
        reference_count=_reference_count(item),
        sources=(OpenAlexProvider.name,),
        access_status=access_status,
    )


def _reconstruct_abstract(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    positions: list[tuple[int, str]] = []
    for word, raw_positions in value.items():
        if not isinstance(word, str) or not isinstance(raw_positions, list):
            continue
        for position in raw_positions:
            if isinstance(position, int) and position >= 0:
                positions.append((position, word))
    if not positions:
        return None
    return " ".join(word for _, word in sorted(positions))


def _reference_count(item: Mapping[str, Any]) -> int | None:
    explicit = _nonnegative_int(item.get("referenced_works_count"))
    if explicit is not None:
        return explicit
    referenced = item.get("referenced_works")
    return len(referenced) if isinstance(referenced, list) else None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) and value > 0 else None


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) and value >= 0 else None
