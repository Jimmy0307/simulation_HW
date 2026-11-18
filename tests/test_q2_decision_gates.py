"""All fixtures synthetic; tests never access a game account."""
from __future__ import annotations
import pytest

from marketplace_sim.q2_decision_gates import (
    ad_budget, incremental_units_to_cover_spend,
    price_change_break_even_uplift, proforma_cash_gates,
    sales_equivalent_forecast,
)


def test_staff_service_fraction_not_full_time() -> None:
    a = sales_equivalent_forecast(5, 2, per_seller_units=30, support_selling_fraction=.25)
    assert a["total_units_sensitivity"] == 165
    b = sales_equivalent_forecast(5, 2, per_seller_units=30, support_selling_fraction=0)
    assert b["total_units_sensitivity"] == 150


def test_ad_cap_counts_design_plus_placement() -> None:
    r = ad_budget(
        brand_ads=2, cost_per_ad=1000,
        media_insertions={"A":2,"B":1},
        media_price_per_insert={"A":2000,"B":500},
        combined_cap=6500,
    )
    assert r["combined_spend"] == 6500
    assert r["within_combined_cap"]
    assert not ad_budget(
        brand_ads=2, cost_per_ad=1000,
        media_insertions={"A":3}, media_price_per_insert={"A":2000},
        combined_cap=6500,
    )["within_combined_cap"]


def test_prices_and_break_even_math() -> None:
    assert price_change_break_even_uplift(100, 90, 50) == pytest.approx(.25)
    assert incremental_units_to_cover_spend(1000, 200) == pytest.approx(5)
    with pytest.raises(ValueError):
        price_change_break_even_uplift(90, 40, 50)


def test_cash_stress_requires_all_scenarios() -> None:
    assert proforma_cash_gates(None, normal_minimum=500, half_demand_minimum=300)["status"].startswith("WAITING_")
    assert proforma_cash_gates({"normal":600}, normal_minimum=500,half_demand_minimum=300)["status"] == "MISSING_SCENARIO"
    r=proforma_cash_gates({"normal":550,"half_demand":320,"quarter_demand":10},normal_minimum=500,half_demand_minimum=300)
    assert r["all_pass"]
    bad=proforma_cash_gates({"normal":600,"half_demand":250,"quarter_demand":-1},normal_minimum=500,half_demand_minimum=300)
    assert not bad["all_pass"]
    assert bad["source_not_verified"]


def test_bad_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        sales_equivalent_forecast(2,1,per_seller_units=30,support_selling_fraction=1.2)
    with pytest.raises(ValueError):
        ad_budget(brand_ads=2,cost_per_ad=100,media_insertions={"missing":1},media_price_per_insert={},combined_cap=1000)
