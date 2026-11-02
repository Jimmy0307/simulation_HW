"""Build protocol dataflow edges without asserting unobserved causality."""

from __future__ import annotations

import re
from typing import Any

from marketplace_mcp.model.provenance import EdgeType


def _walk_fields(shape: dict[str, Any] | None, prefix: str = "") -> list[str]:
    if not isinstance(shape, dict) or shape.get("type") != "object":
        return []
    fields: list[str] = []
    props = shape.get("properties", {})
    if isinstance(props, dict):
        for name, child in props.items():
            path = f"{prefix}.{name}" if prefix else str(name)
            fields.append(path)
            if isinstance(child, dict):
                fields.extend(_walk_fields(child, path))
    return fields


def _node_kind(field: str, direction: str, classification: str) -> str:
    token = field.rsplit(".", 1)[-1].casefold()
    if direction == "request":
        if any(part in token for part in ("price", "budget", "advert", "capacity", "brand", "target", "segment", "salary", "compensation", "decision")):
            return "INPUT_DECISION"
        return "MARKET_DATA"
    if re.search(r"(?i)(revenue|sales|demand|share|profit|cash|cost|score|margin|productivity|capacity|forecast|balance|income)", token):
        return "FINANCIAL_METRIC" if any(part in token for part in ("revenue", "profit", "cash", "cost", "margin", "income", "balance")) else "OUTPUT_METRIC"
    if classification in {"WRITE", "STATE_TRACKING", "FINALIZATION"}:
        return "INTERMEDIATE_STATE"
    return "UNKNOWN"


def build_decision_graph(rpc_methods: list[dict[str, Any]], calculations: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for method in rpc_methods:
        service = str(method.get("service", "UNKNOWN"))
        rpc_name = str(method.get("method", "UNKNOWN"))
        method_id = f"rpc:{service}.{rpc_name}"
        nodes[method_id] = {
            "id": method_id,
            "label": f"{service}.{rpc_name}",
            "type": "INTERMEDIATE_STATE",
            "classification": method.get("classification", "UNKNOWN"),
            "provenance": "VERIFIED_NETWORK_TRACE",
        }
        for direction, shape_key in (("request", "parameter_shape"), ("response", "response_shape")):
            for field_path in _walk_fields(method.get(shape_key)):
                field_id = f"{direction}:{service}:{field_path}"
                kind = _node_kind(field_path, direction, str(method.get("classification", "UNKNOWN")))
                nodes.setdefault(
                    field_id,
                    {
                        "id": field_id,
                        "label": field_path,
                        "type": kind,
                        "classification": method.get("classification", "UNKNOWN"),
                        "provenance": "VERIFIED_NETWORK_TRACE",
                    },
                )
                source, target = (field_id, method_id) if direction == "request" else (method_id, field_id)
                edge_key = (source, target, direction)
                edges[edge_key] = {
                    "source": source,
                    "target": target,
                    "type": str(EdgeType.OBSERVED_DEPENDENCY),
                    "provenance": "VERIFIED_NETWORK_TRACE",
                    "confidence": 1.0,
                    "reason": f"Field is present in an observed {direction} schema for this RPC method; this records data flow and does not establish business causality.",
                    "evidence": list(method.get("evidence_refs", [])),
                }
    for calculation in calculations:
        if calculation.get("classification") != "EXACT_CLIENT_FORMULA":
            continue
        metric = str(calculation.get("metric") or calculation.get("name", "unknown"))
        metric_id = f"metric:{metric}"
        nodes.setdefault(
            metric_id,
            {"id": metric_id, "label": metric, "type": "OUTPUT_METRIC", "provenance": "VERIFIED_CLIENT_CODE"},
        )
        for input_name in calculation.get("inputs", []):
            input_id = f"decision:{input_name}"
            input_type = (
                "INPUT_DECISION"
                if re.search(r"(?i)(price|advert|brand|product|capacity|compensation|salary|wage|worker|channel|budget|segment|strategy)", str(input_name))
                else "INTERMEDIATE_STATE"
                if str(input_name).startswith("this.")
                else "UNKNOWN"
            )
            nodes.setdefault(
                input_id,
                {"id": input_id, "label": input_name, "type": input_type, "provenance": "VERIFIED_CLIENT_CODE"},
            )
            edges[(input_id, metric_id, "formula")] = {
                "source": input_id,
                "target": metric_id,
                "type": str(EdgeType.DIRECT_FORMULA),
                "provenance": "VERIFIED_CLIENT_CODE",
                "confidence": 1.0,
                "reason": "The client contains a pure arithmetic return expression over this declared parameter.",
                "evidence": [calculation.get("source_file", "UNKNOWN"), calculation.get("source_location", "UNKNOWN")],
            }
    return {
        "format_version": 1,
        "nodes": sorted(nodes.values(), key=lambda item: item["id"]),
        "edges": [edges[key] for key in sorted(edges)],
        "causal_limit": "Only observed request/response dataflow and verified pure client formulas are represented. Cross-quarter decision causality requires controlled runtime experiments.",
    }


def trace_decision(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    nodes = {item["id"]: item for item in graph.get("nodes", [])}
    if node_id not in nodes:
        return {"node": node_id, "found": False, "paths": []}
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in graph.get("edges", []):
        adjacency.setdefault(edge.get("source", ""), []).append(edge)
    paths: list[list[str]] = []
    frontier: list[tuple[str, list[str]]] = [(node_id, [node_id])]
    seen_depth: dict[str, int] = {node_id: 0}
    while frontier and len(paths) < 100:
        current, path = frontier.pop(0)
        for edge in adjacency.get(current, []):
            nxt = edge["target"]
            next_path = path + [nxt]
            if nodes.get(nxt, {}).get("type") in {"OUTPUT_METRIC", "FINANCIAL_METRIC", "PERFORMANCE_METRIC"}:
                paths.append(next_path)
            elif len(next_path) <= 8 and seen_depth.get(nxt, 99) >= len(next_path):
                seen_depth[nxt] = len(next_path)
                frontier.append((nxt, next_path))
    return {"node": nodes[node_id], "found": True, "paths": paths, "causal_limit": graph.get("causal_limit")}
