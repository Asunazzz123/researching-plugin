"""Minimal JSON-over-HTTP transport with injectable tests."""

from __future__ import annotations

import json
from typing import Any, Mapping, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class JsonHttpClient(Protocol):
    """Transport boundary used by external scholarly-data adapters."""

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        """Return a decoded JSON object from an HTTP GET request."""

        ...


class UrllibJsonClient:
    """Standard-library JSON client suitable for low-volume metadata calls."""

    def __init__(self, *, timeout: float = 20.0) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._timeout = timeout

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        query = urlencode(params or {})
        target = f"{url}?{query}" if query else url
        request = Request(
            target,
            headers={"Accept": "application/json", **dict(headers or {})},
        )
        with urlopen(request, timeout=self._timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise ValueError("JSON endpoint returned a non-object payload")
        return payload
