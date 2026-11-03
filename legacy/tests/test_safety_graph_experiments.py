from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest

from marketplace_mcp.adapter.registry import MarketplaceServiceRegistry
from marketplace_mcp.adapter.rpc import MarketplaceRPCClient
from marketplace_mcp.adapter.session import MarketplaceSession
from marketplace_mcp.experiments.interactions import supported_pairs
from marketplace_mcp.experiments.sensitivity import finite_difference
from marketplace_mcp.experiments.specification import (
    ALLOW_FINAL_SUBMIT,
    ALLOW_WRITE,
    BaselineState,
    DecisionVariable,
    propose_one_factor_experiment,
)
from marketplace_mcp.graph.builder import build_decision_graph, trace_decision
from marketplace_mcp.security.redaction import safe_shape


def test_safe_shape_omits_sensitive_values_and_keys() -> None:
    shape = safe_shape({"studentId": "student_1", "cash": 123.4, "email": "user@example.test"})
    serialized = json.dumps(shape)
    assert "student_1" not in serialized
    assert "user@example.test" not in serialized
    assert "123.4" not in serialized
    assert "_sensitive_field_redacted" in serialized


def test_session_validates_host_and_hides_credentials_from_repr() -> None:
    session = MarketplaceSession("https://marketplace.example", "marketplace.example", "cookie-value", "csrf-value")
    assert "cookie-value" not in repr(session)
    assert "csrf-value" not in repr(session)
    with pytest.raises(ValueError):
        MarketplaceSession("https://other.example", "marketplace.example", "cookie-value")
    with pytest.raises(ValueError):
        MarketplaceSession("http://marketplace.example", "marketplace.example", "cookie-value")
    with pytest.raises(ValueError, match="X-prefixed"):
        MarketplaceSession("https://marketplace.example", "marketplace.example", "cookie-value", csrf_header="Host")
    with pytest.raises(ValueError, match="line breaks"):
        MarketplaceSession(
            "https://marketplace.example", "marketplace.example", "cookie-value\r\nHost: example.test"
        )


def test_rpc_client_blocks_unobserved_and_write_methods_without_network(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "services": [
                    {
                        "name": "MarketSize",
                        "methods": [
                            {
                                "name": "view",
                                "classification": "READ",
                                "http_method": "POST",
                                "endpoint": "/mpl/backend-json.php?MarketSize",
                                "parameter_shapes": [safe_shape({"method": "view", "parameters": []})],
                            },
                            {"name": "save", "classification": "WRITE", "http_method": "POST", "endpoint": "/mpl/backend-json.php?MarketSize"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    client = MarketplaceRPCClient(
        MarketplaceSession("https://marketplace.example", "marketplace.example", "runtime-cookie"),
        MarketplaceServiceRegistry(registry_path),
    )
    with pytest.raises(ValueError, match="not observed"):
        client.call_read("MarketSize", "unknown")
    with pytest.raises(PermissionError, match="Only observed READ"):
        client.call_read("MarketSize", "save")
    with pytest.raises(PermissionError, match="request shape was not observed"):
        client.call_read("MarketSize", "view", ["unexpected-shape"])

    class FakeOpener:
        request = None

        def open(self, request, timeout):
            self.request = request
            return BytesIO(b"{\"synthetic\":true}")

    fake_opener = FakeOpener()
    client._opener = fake_opener
    assert client.call_read("MarketSize", "view") == {"synthetic": True}
    assert fake_opener.request is not None
    assert fake_opener.request.get_header("Cookie") == "runtime-cookie"

    registry = client.registry
    registry.document["services"][0]["methods"][0]["endpoint"] = "//other.example/backend-json.php?MarketSize"
    with pytest.raises(PermissionError, match="outside the explicitly configured Marketplace host"):
        client.call_read("MarketSize", "view")


def test_graph_records_dataflow_without_causal_claims() -> None:
    methods = [
        {
            "service": "CustomerNeeds",
            "method": "view",
            "classification": "READ",
            "parameter_shape": {"type": "object", "properties": {"segment": {"type": "string"}}},
            "response_shape": {"type": "object", "properties": {"demand": {"type": "number"}}},
            "evidence_refs": ["capture_001:entry_1"],
        }
    ]
    graph = build_decision_graph(methods, [])
    data_edges = [edge for edge in graph["edges"] if edge["type"] == "OBSERVED_DEPENDENCY"]
    assert data_edges
    assert all("does not establish business causality" in edge["reason"] for edge in data_edges)
    traced = trace_decision(graph, "rpc:CustomerNeeds.view")
    assert traced["found"]
    assert traced["paths"] == [["rpc:CustomerNeeds.view", "response:CustomerNeeds:demand"]]
    assert "requires controlled runtime experiments" in traced["causal_limit"]


def test_experiment_requires_evidence_and_never_enables_mutation() -> None:
    variable = DecisionVariable("price", minimum=1, maximum=10, step=1, evidence=["VERIFIED_RENDERED_HTML"], provenance="VERIFIED_NETWORK_TRACE")
    experiment = propose_one_factor_experiment(variable, "demand", BaselineState({"price": 5}), delta=2)
    assert [item.offset for item in experiment.perturbations] == [0, -2, 2]
    assert experiment.dry_run and experiment.read_only
    assert not ALLOW_WRITE and not ALLOW_FINAL_SUBMIT
    with pytest.raises(ValueError):
        propose_one_factor_experiment(DecisionVariable("x"), "y", BaselineState({"x": 1}))
    with pytest.raises(ValueError):
        propose_one_factor_experiment(variable, "demand", BaselineState({"price": float("inf")}))


def test_sensitivity_and_supported_interactions() -> None:
    result = finite_difference("price", "demand", (10, 50), [(8, 60), (12, 40)])
    assert result.central_difference == -5
    variables = [
        DecisionVariable("price", evidence=["capture"], provenance="VERIFIED_NETWORK_TRACE"),
        DecisionVariable("advertising", evidence=["capture"], provenance="VERIFIED_NETWORK_TRACE"),
        DecisionVariable("unsupported", evidence=["capture"], provenance="VERIFIED_NETWORK_TRACE"),
    ]
    assert supported_pairs(variables) == [("advertising", "price")]
