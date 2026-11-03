from __future__ import annotations

import json
from pathlib import Path

from marketplace_mcp.discovery.calculation_finder import classify_metrics
from marketplace_mcp.discovery.har_parser import parse_har_file, summarize_observations
from marketplace_mcp.discovery.html_parser import _safe_route, parse_html_file
from marketplace_mcp.discovery.js_analyzer import analyze_javascript
from marketplace_mcp.discovery.shapes import endpoint_path, method_classification

FIXTURES = Path(__file__).parents[1] / "fixtures" / "synthetic"


def test_html_extracts_quarter_safe_navigation_and_assets() -> None:
    page = parse_html_file(FIXTURES / "sample.html", source_file="page_001.html")
    assert page["quarter"] == 2
    assert page["title"] == "Market Potential"
    assert "core.js" not in page["script_paths"]
    labels = {item["label"] for item in page["elements"]}
    assert "Market Research" in labels
    assert "Price Willing to Pay" in labels
    assert "Next Quarter" in labels


def test_html_omits_unapproved_private_label() -> None:
    from marketplace_mcp.discovery.html_parser import parse_html

    page = parse_html(
        "<html><body><a>Student 24680</a><a>Marketing Research</a></body></html>",
        source_file="page_001.html",
    )
    labels = {item["label"] for item in page["elements"]}
    assert "Student 24680" not in labels
    assert "Marketing Research" in labels


def test_har_extracts_rpc_shape_without_values() -> None:
    observations = parse_har_file(FIXTURES / "sample.har.json", evidence_ref="capture_001")
    assert len(observations) == 1
    observation = observations[0]
    assert observation.service == "MarketSize"
    assert observation.rpc_method == "view"
    assert observation.classification == "READ"
    assert observation.quarter == 2
    assert observation.endpoint == "/mpl/web7/backend-json.php?MarketSize"
    assert observation.response_shape == {
        "type": "object",
        "properties": {"marketSize": {"type": "number"}},
    }
    assert "12500" not in json.dumps(observation.to_dict())
    summary = summarize_observations(observations)
    assert summary["methods"][0]["observed_count"] == 1


def test_rpc_route_and_method_classes() -> None:
    assert endpoint_path("https://host.example/mpl/web7/backend-json.php?MarketSize") == "/mpl/web7/backend-json.php?MarketSize"
    assert method_classification("submitQuarter") == "FINALIZATION"
    assert method_classification("saveSettings") == "WRITE"
    assert method_classification("view") == "READ"
    assert method_classification("gs") == "UNKNOWN"
    private_asset = endpoint_path("https://host.example/mpl/web7/assets/Team_3-private-report.png?token=private")
    assert private_asset == "/mpl/web7/:resource/:asset.png"
    assert "Team_3" not in private_asset
    assert _safe_route("/mpl/web7/private-team.php?studentId=student_1") == "/mpl/web7/:resource"


def test_static_analyzer_recovers_arithmetic_and_call_edges() -> None:
    source = "function quarterlyCapacity(s) { return s * this.maxDays; } function refreshResource(){ fetchResource(); }"
    analysis = analyze_javascript(source, source_file="synthetic.js")
    assert any(item["name"] == "quarterlyCapacity" and item["classification"] == "EXACT_CLIENT_FORMULA" for item in analysis["calculations"])
    assert any(edge["caller"] == "refreshResource" and edge["callee"] == "fetchResource" for edge in analysis["call_edges"])


def test_static_analyzer_keeps_name_candidates_unknown() -> None:
    analysis = analyze_javascript(
        "function getDemandMultiplier(segment) { return table[segment]; }",
        source_file="synthetic.js",
    )
    candidate = analysis["calculation_review_candidates"][0]
    assert candidate["name"] == "getDemandMultiplier"
    assert candidate["classification"] == "UNKNOWN"
    assert candidate["expression"] is None
    assert candidate["provenance"] == "VERIFIED_CLIENT_CODE"


def test_calculation_finder_does_not_invent_server_formula() -> None:
    methods = [
        {
            "service": "ProFormaCashFlow",
            "method": "view",
            "parameter_shape": {"type": "object", "properties": {"quarter": {"type": "number"}}},
            "response_shape": {"type": "object", "properties": {"projectedCash": {"type": "number"}}},
            "evidence_refs": ["capture_001:entry_1"],
        }
    ]
    records = classify_metrics(methods, [])
    assert records[0]["metric"] == "projectedCash"
    assert records[0]["classification"] == "SERVER_OPAQUE"
    assert records[0]["formula"] is None
