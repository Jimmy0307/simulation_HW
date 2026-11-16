"""Synthetic-only regression tests: do not publish captured game data."""
from __future__ import annotations

import pytest

from marketplace_mcp.experiments.q2_planning import (
    evaluate_cash_gates, plan_sales_to_capacity, reconcile_quarters, read_har_views,
)


def _section(i: str, value: int) -> dict:
    return {"items": [{"id": i, "quarters": [str(value)]}]}


def test_cash_reconciliation_identifies_stale_proforma() -> None:
    views = {
        "CashFlow": {"staticData": {"sections": [_section("cash", 1000)]}},
        "BalanceSheet": {"staticData": {"sections": [_section("cd", 900)]}},
        "ProFormaCashFlow": {
            "dynamicData": {"items": [
                {"id": "inc_comm", "value": 400},
                {"id": "so", "value": 120},
                {"id": "interest_income", "value": 10},
            ]},
            "calculate": {"items": [{"id": "cash", "quarters": [1010]}]},
        },
        "ExtFactorySimulation": {
            "calculate": {"accounting": {"cash": 1290, "netIncome": -100}}
        },
    }
    result = reconcile_quarters(views)
    assert result["status"] == "RECONCILED"
    assert result["q2_cash_bridge"] == 1290
    assert result["factory_minus_proforma"] == 280
    assert result["q1_cd_separate_from_bank_cash"] == 900


def test_cash_reconciliation_preserves_unknowns() -> None:
    views = {
        "CashFlow": {"staticData": {"sections": [_section("cash", 100)]}},
        "BalanceSheet": {"staticData": {"sections": [_section("cd", 50)]}},
        "ProFormaCashFlow": {
            "dynamicData": {"items": [{"id": "unknown", "value": 20}]},
            "calculate": {"items": [{"id": "cash", "quarters": [100]}]},
        },
        "ExtFactorySimulation": {"calculate": {"accounting": {"cash": 120}}},
    }
    assert reconcile_quarters(views)["status"] == "NEEDS_REVIEW"


def test_missing_factory_calculation_not_interpreted_as_zero() -> None:
    views = {
        "CashFlow": {"staticData": {"sections": [_section("cash", 100)]}},
        "BalanceSheet": {"staticData": {"sections": [_section("cd", 50)]}},
        "ProFormaCashFlow": {
            "dynamicData": {"items": []},
            "calculate": {"items": [{"id": "cash", "quarters": [100]}]},
        },
        "ExtFactorySimulation": {"calculate": {"accounting": {}}},
    }
    assert reconcile_quarters(views)["status"] == "MISSING_SIMULATION_CASH"


def test_sales_forecast_is_never_silently_zero() -> None:
    assert plan_sales_to_capacity(None)["status"] == "WAITING_FOR_SALES_FORECAST"
    with pytest.raises(ValueError):
        plan_sales_to_capacity({"A": -1})


def test_capacity_three_scenarios() -> None:
    plan = plan_sales_to_capacity(
        {"A": 80, "B": 80}, days=65, productivity_pct=70,
        maximum_daily_capacity=16,
    )
    assert plan["scenarios"]["most_likely"]["daily_capacity_with_productivity_heuristic"] == 4
    assert plan["scenarios"]["pessimistic_50pct"]["demand_units"] == 80
    assert plan["scenarios"]["worst_case_25pct"]["demand_units"] == 40


def test_cash_gates_require_real_observed_scenarios() -> None:
    assert evaluate_cash_gates(None)["status"].startswith("WAITING_")
    with pytest.raises(ValueError):
        evaluate_cash_gates({"most_likely": 600000})
    out = evaluate_cash_gates({
        "most_likely": 510000,
        "pessimistic_50pct": 290000,
        "worst_case_25pct": 100000,
    })
    assert out["gates"]["most_likely"]["pass"]
    assert not out["gates"]["pessimistic_50pct"]["pass"]
    assert out["worst_case"]["nonnegative"]


def test_empty_har_contains_no_auth_or_game_data() -> None:
    assert read_har_views({"log": {"entries": []}}) == {}
