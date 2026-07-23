"""Windows authentication secrets stored through the native keyring backend."""

from __future__ import annotations

import sys
from typing import Any

from ..base import KeyringCredentialStore, UnsupportedPlatformError


class WindowsCredentialStore(KeyringCredentialStore):
    """Store secrets in the current user's Windows Credential Manager."""

    DEFAULT_SERVICE = "researching-plugin.credentials.windows"

    def __init__(
        self,
        service_name: str | None = None,
        *,
        backend: Any | None = None,
        platform_name: str | None = None,
    ) -> None:
        selected_platform = platform_name or sys.platform
        if selected_platform != "win32":
            raise UnsupportedPlatformError(
                "WindowsCredentialStore can only be used on Windows"
            )
        using_injected_backend = backend is not None
        super().__init__(service_name or self.DEFAULT_SERVICE, backend=backend)
        if not using_injected_backend:
            self.require_backend_module("keyring.backends.Windows")
            if hasattr(self._backend, "persist"):
                self._backend.persist = "local machine"
