from __future__ import annotations

import asyncio
import json

import pytest

from marketplace_mcp import server
from marketplace_mcp.experiments.surrogate import fit_surrogate


def test_mcp_registry_and_local_intelligence_tools() -> None:
    tools = asyncio.run(server.mcp.list_tools())
    names = {item.name for item in tools}
    assert len(names) == 22
    assert {"list_modules", "get_rpc_method", "get_decision_graph", "explain_provenance"} <= names
    assert len(server.list_modules()["resources"]) == 6
    assert len(server.list_services()["services"]) == 31
    assert len(server.list_exact_client_formulas()["formulas"]) == 2
    assert len(server.list_server_opaque_metrics()["metrics"]) == 7
    assert server.propose_experiment("price", "cash", 10.0)["status"] == "BLOCKED_UNSUPPORTED_VARIABLE"
    result = asyncio.run(server.mcp.call_tool("get_formula", {"metric": "quarterlyCapacity"}))
    assert not result.is_error
    assert json.loads(result.content[0].text)["classification"] == "EXACT_CLIENT_FORMULA"


def test_surrogate_is_held_out_and_explicitly_approximate() -> None:
    pytest.importorskip("sklearn")
    rows = [{"price": float(x), "demand": float(40 - 3 * x)} for x in range(20)]
    report = fit_surrogate(rows, metric="demand", inputs=["price"], model="ridge", seed=7)
    assert report.sample_count == 20
    assert report.train_count + report.test_count == 20
    assert report.test_count >= 2
    assert report.provenance == "OBSERVED_SURROGATE"
    assert not report.internal_formula_claim
    assert report.mae < 1.0
    assert report.rmse < 1.0
