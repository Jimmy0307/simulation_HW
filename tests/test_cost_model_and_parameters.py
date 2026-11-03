from __future__ import annotations

import base64
import json

import pytest

from marketplace_sysid import cost_model as cm
from marketplace_sysid.parameters import (
    Response,
    build_catalog,
    classify,
    responses_from_scenario,
    unit_of,
)


def test_cd_projection_linear_in_deposit_at_quarter_rate() -> None:
    base = cm.cd_projection(0, cd_prior=0, rate_annual_percent=8)
    step = cm.cd_projection(1000, cd_prior=0, rate_annual_percent=8)
    assert (step.cd - base.cd, step.interest - base.interest) == (1000, 20)
    with pytest.raises(ValueError):
        cm.cd_projection(-1, cd_prior=0, rate_annual_percent=8)


def test_capacity_investment_is_option_row_and_quarter_has_65_days() -> None:
    options = [cm.CapacityOption(0, 0, 0), cm.CapacityOption(5, 70, 1), cm.CapacityOption(10, 140, 2)]
    assert cm.capacity_investment(10, options) == cm.CapacityResult(140, 0.0, 140)
    assert cm.quarterly_units(10) == 650
    with pytest.raises(ValueError):
        cm.capacity_investment(7, options)


def test_opening_costs_add_setup_only_and_refuse_unverified_closing() -> None:
    outlets = [cm.Outlet("a", False, 30, 7), cm.Outlet("b", False, 11, 5), cm.Outlet("c", True, 9, 9)]
    result = cm.store_opening_cost(outlets, {"a": True, "b": True})
    assert result == cm.OpeningCostResult(41, 0.0, 0.0, 41)
    assert cm.web_center_opening_cost(outlets, {}).total == 0
    with pytest.raises(NotImplementedError):
        cm.store_opening_cost(outlets, {"c": True})


def test_stock_issue_identity() -> None:
    result = cm.stock_issue([cm.StockIssue(10, 3), cm.StockIssue(5, 2)], stock_total_prior=100, shares_total_prior=50)
    assert result == cm.StockResult(40, 15, 140, 65)


def test_parameter_classification_and_units() -> None:
    assert classify("staticData.capacityOptions[*].cost") == "parameter_table"
    assert classify("staticData.taxRate") == "parameter"
    assert classify("staticData.cash") == "state_value"
    assert classify("calculate.total") == "result_value"
    assert classify("decisions.increase") == "decision"
    assert classify("staticData.regions[*].regionID") == "identifier"
    assert classify("staticData.chartTemplate.data.percentIncMaxX") == "presentation"
    assert classify("staticData.sections[*].items[*].quarters[*]") == "state_value"
    assert classify("staticData.categories[*].decisions[*].data.calculate.total") == "result_value"
    assert unit_of("staticData.taxRate") == "percent"
    assert unit_of("staticData.regions[*].leaseCost") == "currency"
    assert unit_of("staticData.maxLength") == "characters"


def test_catalog_is_value_free_and_values_are_separate() -> None:
    responses = [Response("Widget", "view", {"staticData": {"options": [{"cost": 123.25, "units": 4}], "rate": 7},
                                             "decisions": {"pick": 4}, "calculate": {"total": 123.25}}, "har")]
    catalog, values = build_catalog(responses)
    text = json.dumps(catalog)
    assert "123.25" not in text and catalog["values_included"] is False
    classes = {row["path"]: row["class"] for row in catalog["fields"]}
    assert classes["staticData.options[*].cost"] == "parameter_table"
    assert values["Widget"]["calculate.total"] == [123.25]


def test_responses_from_scenario_reads_network_content() -> None:
    def body(obj: object) -> dict[str, object]:
        return {"state": "captured", "encoding": "base64", "content": base64.b64encode(json.dumps(obj).encode()).decode()}

    record = {"normalized_result": {"steps": [], "events": {"items": [
        {"kind": "request", "transaction_id": "t", "url": {"url": "https://x.test/backend-json.php?Widget"}},
        {"kind": "network-content", "transaction_id": "t", "phase": "request", "body": body({"method": "view"})},
        {"kind": "network-content", "transaction_id": "t", "phase": "response", "body": body({"result": {"staticData": {"rate": 1}}})},
    ]}}}
    found = list(responses_from_scenario(record))
    assert found == [Response("Widget", "view", {"staticData": {"rate": 1}}, "scenario")]
