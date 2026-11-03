from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load(name: str) -> dict:
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def test_public_assertions_have_evidence_status() -> None:
    modules = load("module_graph.json")
    services = load("service_registry.json")
    observations = load("rpc_observations.json")
    symbols = load("client_symbols.json")
    formulas = load("client_calculations.json")
    metrics = load("calculation_map.json")
    graph = load("decision_graph.json")

    assert modules["provenance"] == "VERIFIED_RENDERED_HTML"
    assert all(item["provenance"] == "VERIFIED_RENDERED_HTML" for item in modules["resources"])
    assert services["provenance"] == "VERIFIED_NETWORK_TRACE"
    assert all(
        method["provenance"] == "VERIFIED_NETWORK_TRACE"
        for service in services["services"]
        for method in service["methods"]
    )
    assert all(item["provenance"] == "VERIFIED_NETWORK_TRACE" for item in observations["observations"])
    assert symbols["provenance"] == "VERIFIED_CLIENT_CODE"
    assert all(item["provenance"] == "VERIFIED_CLIENT_CODE" for item in symbols["functions"])
    assert all(item["provenance"] == "VERIFIED_CLIENT_CODE" for item in formulas["calculations"])
    assert all(item["provenance"] in {"VERIFIED_CLIENT_CODE", "VERIFIED_NETWORK_TRACE"} for item in metrics["metrics"])
    assert all(item.get("provenance") for item in graph["nodes"])
    assert all(item.get("provenance") for item in graph["edges"])
