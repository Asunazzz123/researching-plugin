"""Authenticated encryption for exported browser authentication state."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .base import CredentialStore

_HEADER = b"RSCERT\x00\x01"
_NONCE_SIZE = 12


class InvalidCacheDataError(ValueError):
    """Raised when an encrypted cache is malformed or cannot be authenticated."""


class EncryptedCache:
    """Encrypt cache payloads with a key protected by the native credential store."""

    def __init__(self, store: CredentialStore, cache_id: str) -> None:
        normalized_cache_id = cache_id.strip()
        if not normalized_cache_id or "\x00" in normalized_cache_id:
            raise ValueError("cache_id must be a non-empty string without NUL bytes")
        self._store = store
        self._cache_id = normalized_cache_id
        self._key_account = f"cache-key:{normalized_cache_id}"

    def write_bytes(self, path: str | os.PathLike[str], payload: bytes) -> Path:
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")
        aesgcm = self._aesgcm(self._load_or_create_key())
        nonce = os.urandom(_NONCE_SIZE)
        ciphertext = aesgcm.encrypt(nonce, payload, self._associated_data())
        encoded = _HEADER + nonce + ciphertext
        return self._atomic_write(Path(path), encoded)

    def read_bytes(self, path: str | os.PathLike[str]) -> bytes:
        encoded = Path(path).read_bytes()
        minimum_size = len(_HEADER) + _NONCE_SIZE + 16
        if len(encoded) < minimum_size or not encoded.startswith(_HEADER):
            raise InvalidCacheDataError("cache has an invalid header or length")
        key_text = self._store.load_secret(self._key_account)
        if key_text is None:
            raise InvalidCacheDataError("cache encryption key is unavailable")
        try:
            key = base64.urlsafe_b64decode(key_text.encode("ascii"))
            nonce_start = len(_HEADER)
            nonce_end = nonce_start + _NONCE_SIZE
            return self._aesgcm(key).decrypt(
                encoded[nonce_start:nonce_end],
                encoded[nonce_end:],
                self._associated_data(),
            )
        except Exception as exc:
            raise InvalidCacheDataError(
                "cache authentication failed; the file may be corrupt or copied from another profile"
            ) from exc

    def write_json(
        self,
        path: str | os.PathLike[str],
        value: Any,
    ) -> Path:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return self.write_bytes(path, payload)

    def read_json(self, path: str | os.PathLike[str]) -> Any:
        try:
            return json.loads(self.read_bytes(path).decode("utf-8"))
        except InvalidCacheDataError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidCacheDataError("decrypted cache is not valid JSON") from exc

    def delete(
        self,
        path: str | os.PathLike[str],
        *,
        delete_key: bool = False,
    ) -> None:
        Path(path).unlink(missing_ok=True)
        if delete_key:
            self._store.delete_secret(self._key_account)

    def _associated_data(self) -> bytes:
        return f"researching-plugin:{self._cache_id}:v1".encode("utf-8")

    def _load_or_create_key(self) -> bytes:
        encoded_key = self._store.load_secret(self._key_account)
        if encoded_key is not None:
            try:
                key = base64.b64decode(
                    encoded_key.encode("ascii"),
                    altchars=b"-_",
                    validate=True,
                )
            except (ValueError, UnicodeEncodeError) as exc:
                raise InvalidCacheDataError("stored cache key is malformed") from exc
            if len(key) != 32:
                raise InvalidCacheDataError("stored cache key has an invalid length")
            return key

        key = os.urandom(32)
        self._store.store_secret(
            self._key_account,
            base64.urlsafe_b64encode(key).decode("ascii"),
        )
        return key

    @staticmethod
    def _aesgcm(key: bytes) -> Any:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:
            raise RuntimeError(
                "cryptography is required; install the plugin's requirements.txt"
            ) from exc
        return AESGCM(key)

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> Path:
        parent_existed = path.parent.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not parent_existed:
            try:
                path.parent.chmod(0o700)
            except OSError:
                pass

        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                delete=False,
            ) as temporary_file:
                temporary_name = temporary_file.name
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.chmod(temporary_name, 0o600)
            os.replace(temporary_name, path)
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
        return path
