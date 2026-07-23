"""Shared credential-store contracts."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class CredentialStoreError(RuntimeError):
    """Raised when the operating-system credential store fails."""


class CredentialNotFoundError(CredentialStoreError):
    """Raised when a requested credential is not present."""


class UnsupportedPlatformError(CredentialStoreError):
    """Raised when a platform-specific adapter is used on the wrong system."""


@runtime_checkable
class CredentialStore(Protocol):
    """Minimal secret-store interface used by authentication components."""

    @property
    def service_name(self) -> str:
        """Return the OS credential-store service identifier."""

        ...

    def store_secret(self, account: str, secret: str) -> None:
        """Store or replace a secret for an account."""

        ...

    def load_secret(self, account: str) -> str | None:
        """Return the secret, or None when it is not stored."""

        ...

    def require_secret(self, account: str) -> str:
        """Return the secret or raise CredentialNotFoundError."""

        ...

    def delete_secret(self, account: str) -> bool:
        """Delete the secret and report whether it existed."""

        ...


def _validate_value(label: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    if "\x00" in normalized:
        raise ValueError(f"{label} must not contain NUL bytes")
    return normalized


class KeyringCredentialStore:
    """CredentialStore implementation backed by the active native keyring."""

    def __init__(self, service_name: str, *, backend: Any | None = None) -> None:
        self._service_name = _validate_value("service_name", service_name)
        if backend is None:
            try:
                import keyring
            except ImportError as exc:
                raise CredentialStoreError(
                    "keyring is required; install the plugin's requirements.txt"
                ) from exc
            backend = keyring.get_keyring()
        self._backend = backend

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def backend_name(self) -> str:
        backend_type = type(self._backend)
        return f"{backend_type.__module__}.{backend_type.__qualname__}"

    def require_backend_module(self, module_prefix: str) -> None:
        """Reject configured plaintext or third-party backends in production."""

        if not self.backend_name.startswith(module_prefix):
            raise CredentialStoreError(
                f"expected native backend {module_prefix!r}, got {self.backend_name!r}"
            )

    def store_secret(self, account: str, secret: str) -> None:
        normalized_account = _validate_value("account", account)
        if not isinstance(secret, str):
            raise TypeError("secret must be a string")
        if not secret:
            raise ValueError("secret must not be empty")
        try:
            self._backend.set_password(
                self._service_name,
                normalized_account,
                secret,
            )
        except Exception as exc:
            raise CredentialStoreError(
                f"failed to store credential for {normalized_account!r}"
            ) from exc

    def load_secret(self, account: str) -> str | None:
        normalized_account = _validate_value("account", account)
        try:
            return self._backend.get_password(
                self._service_name,
                normalized_account,
            )
        except Exception as exc:
            raise CredentialStoreError(
                f"failed to load credential for {normalized_account!r}"
            ) from exc

    def require_secret(self, account: str) -> str:
        secret = self.load_secret(account)
        if secret is None:
            raise CredentialNotFoundError(
                f"no credential is stored for account {account!r}"
            )
        return secret

    def delete_secret(self, account: str) -> bool:
        normalized_account = _validate_value("account", account)
        if self.load_secret(normalized_account) is None:
            return False
        try:
            self._backend.delete_password(
                self._service_name,
                normalized_account,
            )
        except Exception as exc:
            raise CredentialStoreError(
                f"failed to delete credential for {normalized_account!r}"
            ) from exc
        return True
