"""Rendered-resource records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModuleResource:
    resource: str
    title: str | None
    parent: str | None
    quarter: int | None
    tabs: list[str] = field(default_factory=list)
    decision_screen: bool = False
    observed_services: list[str] = field(default_factory=list)
    status: str = "UNKNOWN"
    provenance: str = "UNKNOWN"
    evidence_ref: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
