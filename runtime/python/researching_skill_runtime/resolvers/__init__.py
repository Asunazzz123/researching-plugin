"""Full-text access-location resolvers."""

from .base import AccessResolver
from .unpaywall import UnpaywallResolver

__all__ = ["AccessResolver", "UnpaywallResolver"]
