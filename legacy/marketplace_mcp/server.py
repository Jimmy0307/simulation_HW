"""Local read/intelligence MCP server backed by sanitized public evidence."""

from __future__ import annotations

import json
from math import isfinite
from pathlib import Path
from typing import Any, cast

from mcp.server import MCPServer

from marketplace_mcp.graph.builder import trace_decision as _trace_decision

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
mcp = MCPServer("marketplace-simulation-intelligence")


def _load(name: str, default: Any) -> Any:
    path = DATA_DIR / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_dict(name: str, default: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], _load(name, default))


def _methods() -> list[dict[str, Any]]:
    return [method for service in _load("service_registry.json", {}).get("services", []) for method in service.get("methods", [])]


@mcp.tool()
def list_modules() -> dict[str, Any]:
    """List module/resource nodes reconstructed from sanitized rendered HTML."""
    return _load_dict("module_graph.json", {"resources": []})


@mcp.tool()
def get_module(resource: str) -> dict[str, Any]:
    """Get one module or page by its public evidence alias."""
    items = _load("module_graph.json", {}).get("resources", [])
    return next((item for item in items if item.get("resource") == resource), {"found": False})


@mcp.tool()
def list_services() -> dict[str, Any]:
    """List observed RPC services without values or credentials."""
    return _load_dict("service_registry.json", {"services": []})


@mcp.tool()
def get_service(service: str) -> dict[str, Any]:
    """Return observed methods and value-free schemas for one RPC service."""
    doc = _load("service_registry.json", {"services": []})
    return next((item for item in doc.get("services", []) if item.get("name", "").casefold() == service.casefold()), {"found": False})


@mcp.tool()
def get_rpc_method(service: str, method: str) -> dict[str, Any]:
    """Return a normalized request/response schema and classification."""
    for item in _methods():
        if item.get("service", "").casefold() == service.casefold() and item.get("name", "").casefold() == method.casefold():
            return item
    return {"found": False}


@mcp.tool()
def get_decision_graph() -> dict[str, Any]:
    """Return the evidence-backed protocol/dataflow graph and its causal limits."""
    return _load_dict("decision_graph.json", {"nodes": [], "edges": []})


@mcp.tool()
def trace_decision(node: str) -> dict[str, Any]:
    """Trace recorded dataflow from a graph node to observable output metrics."""
    return _trace_decision(_load("decision_graph.json", {"nodes": [], "edges": []}), node)


@mcp.tool()
def list_metrics() -> dict[str, Any]:
    """List numeric metric fields observed in captured responses."""
    return _load_dict("calculation_map.json", {"metrics": []})


@mcp.tool()
def explain_metric(metric: str) -> dict[str, Any]:
    """Explain the evidence class and inputs observed for a metric field."""
    items = _load("calculation_map.json", {}).get("metrics", [])
    return next((item for item in items if item.get("metric", "").casefold() == metric.casefold()), {"found": False})


@mcp.tool()
def list_exact_client_formulas() -> dict[str, Any]:
    """List pure arithmetic client formulas; candidates are excluded."""
    items = _load("client_calculations.json", {}).get("calculations", [])
    return {"formulas": [item for item in items if item.get("classification") == "EXACT_CLIENT_FORMULA"]}


@mcp.tool()
def get_formula(metric: str) -> dict[str, Any]:
    """Get a verified client formula for a metric, if one was observed."""
    items = _load("client_calculations.json", {}).get("calculations", [])
    item = next((x for x in items if x.get("name", "").casefold() == metric.casefold() and x.get("classification") == "EXACT_CLIENT_FORMULA"), None)
    return item or {"found": False, "classification": "UNKNOWN"}


@mcp.tool()
def list_server_opaque_metrics() -> dict[str, Any]:
    """List response metrics whose server-side formula is not in client evidence."""
    items = _load("calculation_map.json", {}).get("metrics", [])
    return {"metrics": [item for item in items if item.get("classification") in {"SERVER_OPAQUE", "SERVER_RESULT_WITH_OBSERVABLE_INPUTS"}]}


def _service_shape(match: str) -> dict[str, Any]:
    doc = _load("service_registry.json", {"services": []})
    return next((x for x in doc.get("services", []) if match.casefold() in x.get("name", "").casefold()), {"found": False, "availability": "NO_MATCHING_LOCAL_OBSERVATION"})


@mcp.tool()
def get_customer_needs() -> dict[str, Any]:
    """Return local schema/observation metadata for customer-needs data."""
    return _service_shape("CustomerNeeds")


@mcp.tool()
def get_market_segments() -> dict[str, Any]:
    """Return local schema/observation metadata for segment data."""
    return _service_shape("Segment")


@mcp.tool()
def get_market_potential() -> dict[str, Any]:
    """Return local schema/observation metadata for market-potential data."""
    return _service_shape("MarketPotential")


@mcp.tool()
def get_price_willing_to_pay() -> dict[str, Any]:
    """Return local schema/observation metadata for willingness-to-pay data."""
    return _service_shape("PriceWillingToPay")


@mcp.tool()
def list_experiments() -> dict[str, Any]:
    """List saved experiment proposals/results; never executes them."""
    return _load_dict("experiments.json", {"experiments": [], "execution_enabled": False})


@mcp.tool()
def propose_experiment(variable: str, metric: str, baseline_value: float, delta: float = 1.0) -> dict[str, Any]:
    """Generate a dry-run OFAT design from caller-supplied values; sends no requests."""
    graph = _load("decision_graph.json", {"nodes": []})
    eligible = any(item.get("label", "").casefold() == variable.casefold() and item.get("type") == "INPUT_DECISION" for item in graph.get("nodes", []))
    if not eligible:
        return {"status": "BLOCKED_UNSUPPORTED_VARIABLE", "variable": variable, "metric": metric, "dry_run": True, "allow_write": False}
    if not isfinite(delta) or not isfinite(baseline_value):
        return {"status": "INVALID_NUMERIC_VALUE", "dry_run": True, "allow_write": False}
    if delta <= 0:
        return {"status": "INVALID_DELTA", "dry_run": True, "allow_write": False}
    return {
        "status": "PROPOSED_NOT_EXECUTED",
        "design": "ONE_FACTOR_AT_A_TIME",
        "variable": variable,
        "metric": metric,
        "baseline_value": baseline_value,
        "perturbations": [0.0, -delta, delta],
        "dry_run": True,
        "read_only": True,
        "allow_write": False,
        "allow_final_submit": False,
    }


@mcp.tool()
def get_sensitivity(variable: str) -> dict[str, Any]:
    """Return measured finite differences for one variable, if available."""
    doc = _load("sensitivities.json", {"results": []})
    return {"results": [x for x in doc.get("results", []) if x.get("variable", "").casefold() == variable.casefold()], "status": "OBSERVED_ONLY"}


@mcp.tool()
def get_interactions(variable: str) -> dict[str, Any]:
    """Return evidenced pairwise experiment candidates for one variable."""
    doc = _load("interactions.json", {"pairs": []})
    return {"pairs": [x for x in doc.get("pairs", []) if variable.casefold() in {str(x.get("left", "")).casefold(), str(x.get("right", "")).casefold()}], "status": "PROPOSED_NOT_EXECUTED"}


@mcp.tool()
def get_surrogate_model(metric: str) -> dict[str, Any]:
    """Return validation metrics for an explicitly approximate surrogate."""
    doc = _load("surrogate_models.json", {"models": []})
    return next((x for x in doc.get("models", []) if x.get("metric", "").casefold() == metric.casefold()), {"found": False, "provenance": "UNKNOWN"})


@mcp.tool()
def explain_provenance(entity: str) -> dict[str, Any]:
    """Find provenance records by entity name or evidence alias."""
    doc = _load("provenance.json", {"entities": []})
    return {"entities": [x for x in doc.get("entities", []) if entity.casefold() in json.dumps(x, ensure_ascii=False).casefold()]}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
