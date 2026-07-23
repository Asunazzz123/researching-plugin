"""Infrastructure adapters shared by metadata providers and resolvers."""

from .http import JsonHttpClient, UrllibJsonClient

__all__ = ["JsonHttpClient", "UrllibJsonClient"]
