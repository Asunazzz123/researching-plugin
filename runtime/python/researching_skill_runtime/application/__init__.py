"""Research workflow orchestration and user-facing queue summaries."""

from .discovery import DiscoveryIssue, DiscoveryResult, DiscoveryService
from .factory import create_discovery_service
from .login_gate import LoginNotice, build_login_notice
from .manifest import DownloadManifest
from .queue import ResearchQueue

__all__ = [
    "DiscoveryIssue",
    "DiscoveryResult",
    "DiscoveryService",
    "DownloadManifest",
    "LoginNotice",
    "ResearchQueue",
    "build_login_notice",
    "create_discovery_service",
]
