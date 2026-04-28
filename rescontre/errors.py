from __future__ import annotations

from typing import Any


class RescontreError(Exception):
    """Base exception for all Rescontre SDK errors."""


class RescontreConfigurationError(RescontreError):
    """Raised when the SDK is misconfigured (e.g. missing API key)."""


class RescontreAPIError(RescontreError):
    """Raised when the Rescontre API returns a non-2xx response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        return f"[{self.status_code}] {super().__str__()}"


class AuthenticationError(RescontreAPIError):
    """Raised when the Rescontre facilitator rejects the API key (HTTP 401)."""
