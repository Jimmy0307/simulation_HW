"""Factory scheduler and decision intake. Synthetic numbers only."""

from __future__ import annotations

import pytest

from marketplace_sim.factory import BrandOrder, Schedule, required_operating_capacity, run, sweep
from marketplace_sim.intake import orders_from_views
from marketplace_sim.pack import pack_from_dict
from tests.test_har_and_cost_curve import synthetic_pack_with_table


def pack():
    data = synthetic_pack_with_table()
    data["initial_state"]["fixed_capacity_units"] = 21
    data["production"].update({"min_increase_cost": 1111.0, "var_increase_cpu": 3.0})
    data["extras"] = {"overtime_productivity": [[0, 81.0], [2, 77.0], [4, 69.0]],
                      "overtime_labor_change": [{"overtime": 0, "change": 0}, {"overtime": 1, "change": 90}]}
    return pack_from_dict(data)


ORDERS = [BrandOrder("Alpha-1", "A", ("c1", "c2"), 700.0, 300.0), BrandOrder("Gamma-1", "C", ("c1", "c4"), 1100.0, 200.0)]


def test_capacity_follows_the_help_text_rule() -> None:
    p = pack()
    r = run(p, ORDERS, Schedule(10, 0, 81.0), 1.0)
    assert r.regular_capacity == pytest.approx(10 * 65 * 0.81)
    assert r.produced == pytest.approx(min(500, 10 * 65 * 0.81)) and r.lost == pytest.approx(500 - r.produced)
    assert required_operating_capacity(500, 81.0) == pytest.approx(500 / 65 / 0.81)


def test_overtime_is_used_only_when_demand_needs_it() -> None:
    p = pack()
    low = run(p, ORDERS, Schedule(10, 4, 81.0), 0.5)
    assert low.overtime_hours_used == 0 and low.overtime_premium == 0 and low.idle_units > 0
    high = run(p, ORDERS, Schedule(10, 4, 81.0), 1.2)
    assert 0 < high.overtime_hours_used <= 4 and high.overtime_premium > 0 and high.lost == pytest.approx(0, abs=1e-6)
    assert high.productivity_used < 81.0
    capped = run(p, ORDERS, Schedule(10, 2, 81.0), 3.0)
    assert capped.overtime_hours_used == pytest.approx(2, abs=1e-6) and capped.lost > 0
    assert capped.next_quarter_demand_cut == pytest.approx(0.5 * capped.lost / capped.demand)


def test_idle_capacity_raises_cost_per_unit_and_change_cost_is_charged() -> None:
    p = pack()
    small, large = run(p, ORDERS, Schedule(8, 0, 81.0), 0.5), run(p, ORDERS, Schedule(16, 0, 81.0), 0.5)
    assert small.produced == large.produced and large.unit_cost > small.unit_cost
    assert large.change_cost == pytest.approx(1111 + 3 * 16 * 65)
    assert run(p, ORDERS, Schedule(16, 0, 81.0, previous_operating_capacity=16), 0.5).change_cost == 0
    assert run(p, ORDERS, Schedule(30, 0, 81.0), 1.0).regular_capacity == pytest.approx(21 * 65 * 0.81)  # capped
    rows = sweep(p, ORDERS, [8, 16], [0, 2], [0.5, 1.0], productivity=81.0, reading="brand")
    assert len(rows) == 8 and all(r["reading"] == "brand" for r in rows)


def test_intake_reads_the_entered_decisions() -> None:
    summary = {"staticData": {"categories": [{"decisions": [
        {"run": "ModifyBrand", "data": {"dynamicData": {"allBrands": [
            {"brandID": 1, "brandName": "Alpha-1", "brandType": "A", "brandFeatures": ["c1", "c2"]},
            {"brandID": 2, "brandName": "Gamma-1", "brandType": "C", "brandFeatures": ["c1", "c4"]}]}}},
        {"run": "Pricing", "data": {"decisions": {"regions": [{"brands": [
            {"brandID": 1, "sell": True, "price": 701, "priority": 2, "rebate": 0},
            {"brandID": 2, "sell": False, "price": 0, "priority": 0, "rebate": 0}]}]}}},
        {"run": "DemandProjection", "data": {"decisions": {"brands": [{"brandID": 1, "demand": 333}, {"brandID": 2, "demand": 0}]}}},
        {"run": "OperatingCapacity", "data": {"decisions": {"operatingCapacity": 0, "projectedWorkersProductivity": 81}}},
        {"run": "Overtime", "data": {"decisions": {"hoursInDay": 10}}}]}]}}
    out = orders_from_views({"SummaryOfDecisions": summary})
    assert out["orders"] == [{"name": "Alpha-1", "brand_type": "A", "components": ["c1", "c2"], "price": 701.0,
                              "rebate": 0.0, "priority": 2, "forecast": 333.0}]
    assert out["schedule"] == {"operating_capacity": 0.0, "productivity": 81.0, "max_overtime_hours": 2.0}
    assert out["warnings"] == ["operating capacity is 0"]
