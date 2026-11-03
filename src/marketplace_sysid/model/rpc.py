"""Sanitized network observation records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RPCObservation:
    endpoint: str
    http_method: str
    service: str | None
    rpc_method: str | None
    parameter_shape: dict[str, Any] | None
    response_shape: dict[str, Any] | None
    initiator: dict[str, Any] = field(default_factory=dict)
    resource: str | None = None
    quarter: int | None = None
    classification: str = "UNKNOWN"
    provenance: str = "VERIFIED_NETWORK_TRACE"
    evidence_ref: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RPCParameter:
    name: str
    shape: dict[str, Any]
    required: bool | None = None
    provenance: str = "VERIFIED_NETWORK_TRACE"


@dataclass(frozen=True)
class RPCResponseSchema:
    shape: dict[str, Any]
    provenance: str = "VERIFIED_NETWORK_TRACE"


@dataclass(frozen=True)
class RPCMethod:
    name: str
    endpoint: str
    http_method: str
    parameter_shapes: list[dict[str, Any]]
    response_shapes: list[dict[str, Any]]
    classification: str
    observed_count: int
    evidence_refs: list[str] = field(default_factory=list)
    provenance: str = "VERIFIED_NETWORK_TRACE"


@dataclass(frozen=True)
class RPCService:
    name: str
    methods: list[RPCMethod]
    provenance: str = "VERIFIED_NETWORK_TRACE"
