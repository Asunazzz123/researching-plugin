"""Browser-form autofill that keeps secrets outside model-visible arguments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .base import CredentialStore


class LocatorLike(Protocol):
    async def fill(self, value: str) -> None:
        """Fill a form control."""

    async def click(self) -> None:
        """Click a form control."""


class PageLike(Protocol):
    def locator(self, selector: str) -> LocatorLike:
        """Return a browser locator."""


@dataclass(frozen=True, slots=True)
class LoginFormSelectors:
    username: str
    password: str
    submit: str | None = None

    def __post_init__(self) -> None:
        if not self.username.strip() or not self.password.strip():
            raise ValueError("username and password selectors must not be empty")


async def autofill_login_form(
    page: PageLike,
    store: CredentialStore,
    account: str,
    selectors: LoginFormSelectors,
    *,
    submit: bool = False,
) -> None:
    """Fill credentials and optionally submit without logging or returning secrets."""

    if submit and selectors.submit is None:
        raise ValueError("a submit selector is required when submit=True")

    normalized_account = account.strip()
    if not normalized_account:
        raise ValueError("account must not be empty")

    secret = store.require_secret(normalized_account)
    try:
        await page.locator(selectors.username).fill(normalized_account)
        await page.locator(selectors.password).fill(secret)
        if submit:
            assert selectors.submit is not None
            await page.locator(selectors.submit).click()
    finally:
        secret = ""
