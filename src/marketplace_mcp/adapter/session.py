"""Runtime-only session values. Secrets are never serialized or represented."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class MarketplaceSession:
    base_url: str
    expected_host: str
    cookie: str = field(repr=False, compare=False)
    csrf_token: str | None = field(default=None, repr=False, compare=False)
    csrf_header: str = "X-XSRF-TOKEN"

    def __post_init__(self) -> None:
        base = urlsplit(self.base_url)
        expected = self.expected_host.casefold().rstrip(".")
        if base.scheme != "https" or not base.hostname:
            raise ValueError("Marketplace base URL must use HTTPS and include a host.")
        if base.hostname.casefold().rstrip(".") != expected:
            raise ValueError("Marketplace base URL host does not match the explicitly configured expected host.")
        if base.username or base.password or base.query or base.fragment:
            raise ValueError("Base URL must not contain credentials, query parameters, or a fragment.")
        if base.path not in {"", "/"}:
            raise ValueError("Configure the host origin only; observed RPC paths come from the local registry.")
        if not self.cookie:
            raise ValueError("A runtime-only session cookie must be explicitly supplied.")
        if "\r" in self.cookie or "\n" in self.cookie or (
            self.csrf_token is not None and any(char in self.csrf_token for char in "\r\n")
        ):
            raise ValueError("Runtime session values must not contain line breaks.")
        if not re.fullmatch(r"(?i)x-[a-z0-9-]{1,60}", self.csrf_header):
            raise ValueError("The CSRF header must be a valid X-prefixed header name.")

    @classmethod
    def from_env(cls) -> MarketplaceSession:
        """Load credentials from the parent process environment at runtime."""
        base_url = os.environ.get("MARKETPLACE_BASE_URL", "")
        expected_host = os.environ.get("MARKETPLACE_EXPECTED_HOST", "")
        cookie = os.environ.get("MARKETPLACE_COOKIE", "")
        csrf_token = os.environ.get("MARKETPLACE_CSRF_TOKEN")
        csrf_header = os.environ.get("MARKETPLACE_CSRF_HEADER", "X-XSRF-TOKEN")
        if not base_url or not expected_host or not cookie:
            raise RuntimeError("Marketplace runtime session is not configured in the environment.")
        return cls(base_url, expected_host, cookie, csrf_token, csrf_header)

    def request_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json", "Cookie": self.cookie}
        if self.csrf_token:
            headers[self.csrf_header] = self.csrf_token
        return headers
