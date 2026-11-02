"""Metric and calculation records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CalculationRecord:
    metric: str
    classification: str
    formula: str | None
    inputs: list[str]
    outputs: list[str]
    client_evidence: list[str] = field(default_factory=list)
    rpc_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    notes: str = ""
    provenance: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
