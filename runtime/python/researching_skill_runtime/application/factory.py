"""Convenience assembly for the default anonymous discovery workflow."""

from __future__ import annotations

from researching_skill_runtime.providers import (
    CrossrefProvider,
    MetadataProvider,
    OpenAlexProvider,
)
from researching_skill_runtime.resolvers import AccessResolver, UnpaywallResolver

from .discovery import DiscoveryService


def create_discovery_service(
    *,
    crossref_mailto: str | None = None,
    openalex_api_key: str | None = None,
    unpaywall_email: str | None = None,
) -> DiscoveryService:
    """Assemble public providers without requiring institutional login."""

    providers: list[MetadataProvider] = [
        CrossrefProvider(mailto=crossref_mailto)
    ]
    if openalex_api_key:
        providers.append(OpenAlexProvider(openalex_api_key))

    resolvers: list[AccessResolver] = []
    if unpaywall_email:
        resolvers.append(UnpaywallResolver(unpaywall_email))
    return DiscoveryService(providers, resolvers=resolvers)
