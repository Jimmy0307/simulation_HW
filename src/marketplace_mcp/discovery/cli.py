"""Generate value-free public artifacts from private browser evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from marketplace_mcp.discovery.calculation_finder import classify_metrics
from marketplace_mcp.discovery.har_parser import parse_har_file, summarize_observations
from marketplace_mcp.discovery.html_parser import parse_html_file, summarize_pages
from marketplace_mcp.discovery.js_analyzer import analyze_javascript_file, summarize_javascript
from marketplace_mcp.graph.builder import build_decision_graph
from marketplace_mcp.model.rpc import RPCObservation

_JS_WORDS = re.compile(r"(?is)(?:function\s*\w*\s*\(|\b(?:const|let|var)\s+\w+\s*=|window\.|backend-json\.php)")
_CAPTURE_EXTENSIONS = {".har", ".devtools"}
_TEXT_EXTENSIONS = {".html", ".htm", ".js", ".mjs", ".cjs", ".download", ".下載", ".txt"}


def _json_has_entries(path: Path) -> bool:
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(doc, dict):
        return False
    log = doc.get("log", doc)
    return isinstance(log, dict) and isinstance(log.get("entries"), list)


def _is_javascript(path: Path) -> bool:
    if path.suffix.casefold() in {".js", ".mjs", ".cjs"}:
        return True
    if path.suffix.casefold() not in _TEXT_EXTENSIONS:
        return False
    try:
        sample = path.read_text(encoding="utf-8", errors="replace")[:32_000]
    except OSError:
        return False
    return bool(_JS_WORDS.search(sample)) and "<html" not in sample[:4096].casefold()


def _safe_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def discover(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    input_dir = input_dir.resolve()
    files = sorted(path for path in input_dir.rglob("*") if path.is_file())
    html_files = [path for path in files if path.suffix.casefold() in {".html", ".htm"}]
    js_files = [path for path in files if _is_javascript(path)]
    capture_files = [path for path in files if path.suffix.casefold() in _CAPTURE_EXTENSIONS or (path.suffix.casefold() == ".json" and _json_has_entries(path))]
    private_map: dict[str, str] = {}
    pages: list[dict[str, Any]] = []
    scripts: list[dict[str, Any]] = []
    observations: list[RPCObservation] = []
    for index, path in enumerate(html_files, 1):
        alias = f"page_{index:03d}.html"
        private_map[alias] = str(path.relative_to(input_dir))
        pages.append(parse_html_file(path, source_file=alias))
    seen_js_digests: set[str] = set()
    for path in js_files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen_js_digests:
            continue
        seen_js_digests.add(digest)
        index = len(scripts) + 1
        alias = f"client_asset_{index:03d}.js"
        private_map[alias] = str(path.relative_to(input_dir))
        scripts.append(analyze_javascript_file(path, source_file=alias))
    for index, path in enumerate(capture_files, 1):
        alias = f"capture_{index:03d}"
        private_map[alias] = str(path.relative_to(input_dir))
        try:
            observations.extend(parse_har_file(path, evidence_ref=alias))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue

    module_doc: dict[str, Any] = summarize_pages(pages)
    symbol_doc: dict[str, Any] = summarize_javascript(scripts)
    call_edges = []
    seen_edges: set[tuple[str, str, str, str]] = set()
    for script in scripts:
        for edge in script["call_edges"]:
            key = (edge["caller"], edge["callee"], edge["source_file"], edge["source_location"])
            if key not in seen_edges:
                seen_edges.add(key)
                call_edges.append(edge)
    call_graph = {"format_version": 1, "edges": call_edges, "provenance": "VERIFIED_CLIENT_CODE"}
    rpc_doc: dict[str, Any] = summarize_observations(observations)
    registry: dict[str, dict[str, Any]] = {}
    for method in rpc_doc["methods"]:
        if method["service"] == "UNKNOWN" or method["method"] == "UNKNOWN":
            continue
        service_name = method["service"]
        service = registry.setdefault(service_name, {"name": service_name, "methods": [], "provenance": "VERIFIED_NETWORK_TRACE"})
        service["methods"].append(
            {
                "name": method["method"],
                "provenance": "VERIFIED_NETWORK_TRACE",
                "endpoint": method["endpoint"],
                "http_method": method["http_method"],
                "parameter_shape": method["parameter_shape"],
                "response_shape": method["response_shape"],
                "parameter_shapes": method["parameter_shapes"],
                "response_shapes": method["response_shapes"],
                "classification": method["classification"],
                "observed_count": method["observed_count"],
                "initiators": method["initiators"],
                "resources": method["resources"],
                "quarters": method["quarters"],
                "evidence_refs": method["evidence_refs"],
            }
        )
    for service in registry.values():
        service["methods"].sort(key=lambda item: item["name"])
    service_doc: dict[str, Any] = {
        "format_version": 1,
        "services": [registry[key] for key in sorted(registry)],
        "provenance": "VERIFIED_NETWORK_TRACE",
    }
    client_calculations: list[dict[str, Any]] = [
        calculation for script in scripts for calculation in script["calculations"]
    ]
    exact_locations = {
        (item["name"], item["source_file"], item["source_location"])
        for item in client_calculations
        if item.get("classification") == "EXACT_CLIENT_FORMULA"
    }
    calculation_review_candidates: list[dict[str, Any]] = [
        candidate
        for script in scripts
        for candidate in script["calculation_review_candidates"]
        if (candidate["name"], candidate["source_file"], candidate["source_location"]) not in exact_locations
    ]
    calculation_doc: dict[str, Any] = {
        "format_version": 1,
        "provenance": "VERIFIED_CLIENT_CODE",
        "calculations": client_calculations,
        "review_candidates": calculation_review_candidates,
    }
    metric_doc: dict[str, Any] = {
        "format_version": 1,
        "provenance": "VERIFIED_NETWORK_TRACE",
        "metrics": classify_metrics(rpc_doc["methods"], client_calculations),
    }
    graph_doc = build_decision_graph(rpc_doc["methods"], client_calculations)
    observations_doc = {
        "format_version": 1,
        "provenance": "VERIFIED_NETWORK_TRACE",
        "observations": [item.to_dict() for item in observations],
    }
    _write_json(output_dir / "module_graph.json", module_doc)
    _write_json(output_dir / "client_symbols.json", symbol_doc)
    _write_json(output_dir / "client_call_graph.json", call_graph)
    _write_json(output_dir / "client_calculations.json", calculation_doc)
    _write_json(output_dir / "rpc_observations.json", observations_doc)
    _write_json(output_dir / "service_registry.json", service_doc)
    _write_json(output_dir / "calculation_map.json", metric_doc)
    _write_json(output_dir / "decision_graph.json", graph_doc)
    (input_dir.parent / "evidence_aliases.json").write_text(
        json.dumps(private_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {
        "input_files": len(files),
        "html_files": len(html_files),
        "javascript_files": len(scripts),
        "javascript_file_copies": len(js_files),
        "capture_files": len(capture_files),
        "rpc_observations": len(observations),
        "services": len(service_doc["services"]),
        "rpc_methods": sum(len(item["methods"]) for item in service_doc["services"]),
        "client_functions": symbol_doc["function_count"],
        "client_formula_records": len(client_calculations),
        "exact_client_formulas": sum(item.get("classification") == "EXACT_CLIENT_FORMULA" for item in client_calculations),
        "calculation_review_candidates": len(calculation_review_candidates),
        "metric_records": len(metric_doc["metrics"]),
        "resources": len(module_doc["resources"]),
        "output_dir": str(output_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("evidence/private/extracted"))
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    print(json.dumps(discover(args.input, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
