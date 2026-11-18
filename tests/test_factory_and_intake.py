"""Factory scheduler and decision intake. Synthetic numbers only."""

from __future__ import annotations

from typing import Any, ClassVar

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


# --- the engine's just-in-time factory (plan 'factory' block) -------------------------------------------------------

class FixedDemand:
    level = __import__("marketplace_sim.provenance", fromlist=["Level"]).Level.LITERATURE
    carryover = 0.0
    coefficients: ClassVar[dict[str, Any]] = {"web_weight": 1.0}

    def __init__(self, units: dict[str, float]) -> None:
        self.u = units

    def units(self, pack, offers):
        from marketplace_sim.provenance import Tagged
        return {(o.firm, o.brand): Tagged(self.u.get(o.brand, 0.0) if o.firm == "us" else 0.0, self.level, "test")
                for o in offers}


def jit_state(p):
    from marketplace_sim.engine import CompanyState
    s = CompanyState.initial(p)
    s.fixed_capacity_units = 21
    s.stores_open = [p.stores[0].key]
    return s


def jit_plan(oc: float, ot: float = 0, **extra):
    from marketplace_sim.engine import Plan
    return Plan.from_dict({"factory": {"operating_capacity": oc, "max_overtime_hours": ot, "productivity": 81},
                           "brands": [{"name": "Alpha-1", "brand_type": "A", "components": ["c1", "c2"], "price": 700},
                                      {"name": "Gamma-1", "brand_type": "C", "components": ["c1", "c4"], "price": 1100}],
                           **extra})


def test_engine_builds_what_is_demanded_within_capacity() -> None:
    from marketplace_sim.engine import advance
    from marketplace_sim.reconcile import CASH_ROWS
    p = pack()
    demand = FixedDemand({"Alpha-1": 300, "Gamma-1": 200})
    _, low = advance(jit_state(p), jit_plan(16), p, demand=demand, competitors=[])
    cap = 16 * 65 * 0.81
    assert low.lines["units_sold[Alpha-1]"].value == pytest.approx(300) and low.lines["units_lost_total"].value == 0
    assert low.lines["factory_idle_units"].value == pytest.approx(cap - 500)
    assert low.lines["factory_excess_capacity_cost"].value > 0
    direct = run(p, [BrandOrder("Alpha-1", "A", ("c1", "c2"), 700, 300), BrandOrder("Gamma-1", "C", ("c1", "c4"), 1100, 200)],
                 Schedule(16, 0, 81.0), 1.0)
    assert low.lines["production_cost"].value + low.lines["factory_excess_capacity_cost"].value == pytest.approx(direct.production_cost)
    # cash identity: every cash line mapped (excess capacity included)
    flows = sum(sign * low.lines[k].value for k, (_row, sign) in CASH_ROWS.items() if k in low.lines)
    assert low.lines["cash_start"].value + flows == pytest.approx(low.lines["cash_end"].value)
    nxt, high = advance(jit_state(p), jit_plan(6, 2), p, demand=FixedDemand({"Alpha-1": 900, "Gamma-1": 600}), competitors=[])
    assert high.lines["units_lost_total"].value > 0 and high.lines["overtime_hours_used"].value == pytest.approx(2, abs=1e-6)
    assert nxt.demand_cut == pytest.approx(0.5 * high.lines["units_lost_total"].value / 1500)
    assert nxt.operating_capacity == 6
    _, after = advance(nxt, jit_plan(6, 2), p, demand=FixedDemand({"Alpha-1": 100, "Gamma-1": 100}), competitors=[])
    assert after.lines["units_demanded[Alpha-1]"].value == pytest.approx(100 * (1 - nxt.demand_cut))
    assert after.lines["capacity_change_cost"].value == 0  # same operating capacity as last quarter


def test_factory_block_refuses_the_overlapping_modules() -> None:
    from marketplace_sim.engine import advance
    p = pack()
    with pytest.raises(ValueError, match="replaces"):
        advance(jit_state(p), jit_plan(10, modules={"production.excess_capacity": {}}), p,
                demand=FixedDemand({}), competitors=[])


def test_accrual_books_balance_with_the_factory() -> None:
    from marketplace_sim.engine import advance
    p = pack()
    s = jit_state(p)
    for d, oc in (({"Alpha-1": 300, "Gamma-1": 200}, 10), ({"Alpha-1": 900, "Gamma-1": 700}, 10), ({"Alpha-1": 50}, 12)):
        s, r = advance(s, jit_plan(oc, 2, modules={"accounting.accrual": {}}), p, demand=FixedDemand(d), competitors=[])
        assert r.lines["balance_check"].value == pytest.approx(0, abs=1e-5)
        assert r.lines["accrual_cogs"].value == pytest.approx(r.lines["production_cost"].value)  # nothing left in stock
