"""Classify observed metric fields without inventing server-side formulas."""

from __future__ import annotations

import re
from typing import Any

from marketplace_mcp.model.provenance import CalculationClass

_METRIC_TERMS = re.compile(
    r"(?i)(revenue|sales|unit.?sales|demand|market.?share|cogs|gross.?margin|"
    r"operating.?profit|profit|cash|capacity.?utilization|productivity|score|"
    r"brand|preference|forecast|balance|income|price|cost|potential)"
)
_DECISION_INPUT_TERMS = re.compile(
    r"(?i)(price|advert|promotion|brand|product|feature|quality|segment|target|capacity|"
    r"compensation|salary|wage|worker|employee|sales.?coverage|sales.?office|channel|"
    r"production|unit.?cost|variable.?cost|fixed.?cost|budget|objective|strategy|thrust)"
)


def _field_paths(schema: dict[str, Any] | None, prefix: str = "") -> list[tuple[str, str]]:
    if not isinstance(schema, dict):
        return []
    result: list[tuple[str, str]] = []
    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, child in properties.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                child_type = child.get("type", "unknown") if isinstance(child, dict) else "unknown"
                result.append((path, str(child_type)))
                result.extend(_field_paths(child, path))
    elif schema.get("type") == "array":
        for item in schema.get("items", []):
            result.extend(_field_paths(item, prefix + "[]"))
    return result


def classify_metrics(
    rpc_methods: list[dict[str, Any]], client_calculations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    exact_by_name = {str(item.get("name", "")).casefold(): item for item in client_calculations if item.get("classification") == CalculationClass.EXACT_CLIENT_FORMULA}
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for method in rpc_methods:
        response_fields = _field_paths(method.get("response_shape"))
        input_fields = [
            path
            for path, _ in _field_paths(method.get("parameter_shape"))
            if _DECISION_INPUT_TERMS.search(path.rsplit(".", 1)[-1])
            and "sensitive_field" not in path.casefold()
        ]
        for field_path, field_type in response_fields:
            metric = field_path.rsplit(".", 1)[-1].replace("[]", "")
            if field_type != "number" or not _METRIC_TERMS.search(metric) or metric.casefold().startswith("has"):
                continue
            exact = exact_by_name.get(metric.casefold())
            if exact:
                classification = CalculationClass.EXACT_CLIENT_FORMULA
                formula = exact.get("expression")
                evidence = [exact.get("evidence_ref", "VERIFIED_CLIENT_CODE")]
                confidence = float(exact.get("confidence", 1.0))
                notes = "A pure client-side arithmetic expression is present; server processing may still add other outputs."
            elif input_fields:
                classification = CalculationClass.SERVER_RESULT_WITH_OBSERVABLE_INPUTS
                formula = None
                evidence = list(method.get("evidence_refs", []))
                confidence = 0.9
                notes = "The RPC response exposes this field and the request exposes decision-like fields; this does not prove the complete simulation inputs or formula."
            else:
                classification = CalculationClass.SERVER_OPAQUE
                formula = None
                evidence = list(method.get("evidence_refs", []))
                confidence = 0.85
                notes = "The response field is observable; captured request fields contain no identified business decision variable, and the server-side calculation is not present in client evidence."
            key = (metric, str(classification))
            record = records.setdefault(
                key,
                {
                    "metric": metric,
                    "classification": str(classification),
                    "provenance": "VERIFIED_CLIENT_CODE" if exact else "VERIFIED_NETWORK_TRACE",
                    "formula": formula,
                    "inputs": input_fields,
                    "outputs": [field_path],
                    "client_evidence": evidence if exact else [],
                    "rpc_evidence": evidence if not exact else list(method.get("evidence_refs", [])),
                    "confidence": confidence,
                    "notes": notes,
                },
            )
            if field_path not in record["outputs"]:
                record["outputs"].append(field_path)
            record["inputs"] = sorted(set(record["inputs"]) | set(input_fields))
            record["rpc_evidence"] = sorted(set(record["rpc_evidence"]) | set(method.get("evidence_refs", [])))
    return [records[key] for key in sorted(records)]
