"""Read-only RPC client restricted to observed READ contracts and one host."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from marketplace_mcp.adapter.registry import MarketplaceServiceRegistry
from marketplace_mcp.adapter.session import MarketplaceSession
from marketplace_mcp.discovery.shapes import json_shape, service_from_url


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class MarketplaceRPCClient:
    def __init__(
        self,
        session: MarketplaceSession,
        registry: MarketplaceServiceRegistry,
        *,
        timeout: float = 15.0,
    ) -> None:
        self.session = session
        self.registry = registry
        self.timeout = timeout
        self._opener = build_opener(_RejectRedirects())

    def call_read(self, service: str, method: str, parameters: list[Any] | dict[str, Any] | None = None) -> Any:
        contract = self.registry.get_method(service, method)
        if not contract:
            raise ValueError("The requested service/method was not observed in the local evidence registry.")
        if contract.get("classification") != "READ":
            raise PermissionError("Only observed READ methods are enabled; writes and finalization are disabled.")
        if contract.get("http_method") != "POST":
            raise PermissionError("This adapter only supports observed POST RPC methods.")
        endpoint = contract.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint.startswith("/"):
            raise ValueError("Registry endpoint is not a valid relative path.")
        endpoint_parts = urlsplit(endpoint)
        if endpoint_parts.fragment or service_from_url(endpoint) != service:
            raise PermissionError("RPC endpoint does not match the observed service contract.")
        url = urljoin(self.session.base_url.rstrip("/") + "/", endpoint)
        target = urlsplit(url)
        base = urlsplit(self.session.base_url)
        if target.scheme != "https" or target.hostname != base.hostname or target.port != base.port:
            raise PermissionError("RPC target is outside the explicitly configured Marketplace host.")
        payload = {"method": method, "parameters": parameters or []}
        actual_shape = json_shape(payload)
        observed_shapes = contract.get("parameter_shapes") or [contract.get("parameter_shape")]
        if actual_shape is None or actual_shape not in observed_shapes:
            raise PermissionError("RPC request shape was not observed for this method.")
        request = Request(url, data=json.dumps(payload).encode("utf-8"), headers=self.session.request_headers(), method="POST")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise ValueError("RPC response exceeded the local 4 MB safety limit.")
                return json.loads(body.decode("utf-8"))
        except HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                raise PermissionError("Cross-origin or redirected Marketplace RPC responses are blocked.") from None
            raise RuntimeError(f"Marketplace RPC returned HTTP {exc.code}.") from None
        except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
            raise RuntimeError("Marketplace RPC failed; request and credential details were suppressed.") from None
