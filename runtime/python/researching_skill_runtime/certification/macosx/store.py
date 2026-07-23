"""macOS authentication secrets stored through the native Keychain backend."""

from __future__ import annotations

import sys
from typing import Any

from ..base import KeyringCredentialStore, UnsupportedPlatformError


class MacOSCredentialStore(KeyringCredentialStore):
    """Store secrets in the current user's macOS Keychain."""

    DEFAULT_SERVICE = "researching-plugin.credentials.macosx"

    def __init__(
        self,
        service_name: str | None = None,
        *,
        backend: Any | None = None,
        platform_name: str | None = None,
    ) -> None:
        selected_platform = platform_name or sys.platform
        if selected_platform != "darwin":
            raise UnsupportedPlatformError(
                "MacOSCredentialStore can only be used on macOS"
            )
        using_injected_backend = backend is not None
        super().__init__(service_name or self.DEFAULT_SERVICE, backend=backend)
        if not using_injected_backend:
            self.require_backend_module("keyring.backends.macOS")
