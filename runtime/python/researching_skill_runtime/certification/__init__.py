"""Cross-platform credential storage and encrypted authentication caches."""

from __future__ import annotations

import sys
from typing import Any

from .autofill import LoginFormSelectors, autofill_login_form
from .base import (
    CredentialNotFoundError,
    CredentialStore,
    CredentialStoreError,
    UnsupportedPlatformError,
)
from .cache import EncryptedCache, InvalidCacheDataError


def create_credential_store(
    service_name: str | None = None,
    *,
    backend: Any | None = None,
    platform_name: str | None = None,
) -> CredentialStore:
    """Create the native credential-store adapter for the selected platform."""

    selected_platform = platform_name or sys.platform
    if selected_platform == "win32":
        from .windows import WindowsCredentialStore

        return WindowsCredentialStore(
            service_name=service_name,
            backend=backend,
            platform_name=selected_platform,
        )
    if selected_platform == "darwin":
        from .macosx import MacOSCredentialStore

        return MacOSCredentialStore(
            service_name=service_name,
            backend=backend,
            platform_name=selected_platform,
        )
    raise UnsupportedPlatformError(
        f"researching-plugin authentication is unsupported on {selected_platform!r}"
    )


__all__ = [
    "CredentialNotFoundError",
    "CredentialStore",
    "CredentialStoreError",
    "EncryptedCache",
    "InvalidCacheDataError",
    "LoginFormSelectors",
    "UnsupportedPlatformError",
    "autofill_login_form",
    "create_credential_store",
]

