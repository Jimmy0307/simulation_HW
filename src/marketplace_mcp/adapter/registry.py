"""Load normalized, value-free RPC method definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MarketplaceServiceRegistry:
    def __init__(self, path: str | Path = "data/service_registry.json") -> None:
        self.path = Path(path)
        if self.path.exists():
            self.document = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.document = {"services": []}

    def services(self) -> list[dict[str, Any]]:
        services = self.document.get("services", [])
        return services if isinstance(services, list) else []

    def get_service(self, name: str) -> dict[str, Any] | None:
        return next((item for item in self.services() if item.get("name") == name), None)

    def get_method(self, service: str, method: str) -> dict[str, Any] | None:
        item = self.get_service(service)
        if not item:
            return None
        methods = item.get("methods", [])
        return next((entry for entry in methods if entry.get("name") == method), None)

    def is_read_method(self, service: str, method: str) -> bool:
        item = self.get_method(service, method)
        return bool(item and item.get("classification") == "READ")
