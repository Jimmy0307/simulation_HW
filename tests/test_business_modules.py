"""Business modules: framework, ledger consistency, literature ranges, and SANITY tests of every module.

These are not accuracy tests. They check direction, monotonicity, diminishing returns, bounds at extreme inputs,
that literature coefficients stay inside their published range, and that every number downstream carries the weakest
level of what it uses.
"""

from __future__ import annotations

import copy
import dataclasses
import itertools
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from marketplace_sim.api import service as svc
from marketplace_sim.api.export import _plan
from marketplace_sim.business import (
    IMPLEMENTATIONS,
    Maturity,
    ModuleDecisionError,
    catalog,
    ledger_rows,
)
from marketplace_sim.business.inventory import InventoryModule
from marketplace_sim.business.marketing import MediaMixLiterature, effective_ratio, mix_index
from marketplace_sim.business.purchasing import PurchasingHeuristic
from marketplace_sim.business.registry import coefficients, defaults
from marketplace_sim.business.sales_force import SalesForceModule
from marketplace_sim.engine import CompanyState, Plan, advance
from marketplace_sim.pack import load_pack

ROOT = Path(__file__).resolve().parents[1]
PACK = load_pack(ROOT / "examples" / "synthetic")
LEDGER = json.loads((ROOT / "data" / "modeling_ledger.json").read_text(encoding="utf-8"))
DEMAND_CHAIN = ("units_demanded[Alpha-1]", "units_sold[Alpha-1]", "market_share", "market_units_total", "revenue")
pairwise = itertools.pairwise


@pytest.fixture(scope="module")
def after_q1() -> svc.Session:
    session = svc.Session()
    svc.new_game(session)
    svc.play(session, _plan(svc.SYNTHETIC_PLANS / "q1.yaml"))
    return session


def preview(session: svc.Session, modules: dict[str, Any], **brand: Any) -> dict[str, Any]:
    plan = copy.deepcopy(_plan(svc.SYNTHETIC_PLANS / "q2.yaml"))
    plan["brands"][0].update(brand)
    plan["modules"] = modules
    lines: dict[str, Any] = svc.preview(session, plan)["report"]["lines"]
    return lines


def three_quarters(modules_q2: dict[str, Any], modules_q3: dict[str, Any] | None = None) -> list[Any]:
    """q1, q2 (with modules), q3: states and reports, engine only."""
    state = CompanyState.initial(PACK)
    out = []
    for i, name in enumerate(["q1.yaml", "q2.yaml", "q3.yaml"]):
        plan = _plan(svc.SYNTHETIC_PLANS / name)
        if i == 1:
            plan = {**plan, "modules": modules_q2}
        if i == 2 and modules_q3 is not None:
            plan = {**plan, "modules": modules_q3}
        state, report = advance(state, Plan.from_dict(plan), PACK)
        out.append((state, report))
    return out


# --- ledger and framework ---------------------------------------------------------------------------------------------

def test_ledger_rows_are_complete_and_consistent() -> None:
    rows = ledger_rows()
    keys = [r["key"] for r in rows]
    assert len(keys) == len(set(keys))
    areas = {a["id"] for a in LEDGER["areas"]}
    for row in rows:
        assert row["maturity"] in {m.value for m in Maturity}, row["key"]
        assert row["real_status"] in {"measured", "inferred", "unknown"}, row["key"]
        assert row["area"] in areas and row["next_step"] and row["capture"], row["key"]
        assert set(row["sources"]) <= set(LEDGER["sources"]), row["key"]
        if row["real_status"] != "measured":  # anything not captured is explicitly unverified
            assert "unverified" in row["capture"] or "unknown" in row["capture"], row["key"]
    assert {"marketing", "sales_force", "production", "supply", "rnd", "finance", "strategy"} <= {r["area"] for r in rows}
    # progress: the previous round's counts are kept, so the overview can show the change
    assert LEDGER["history"][0]["total"] == 49 and sum(LEDGER["history"][0]["counts"].values()) == 49


def test_every_implementation_matches_its_ledger_rows() -> None:
    rows = {r["key"]: r for r in ledger_rows()}
    for key, impl in IMPLEMENTATIONS.items():
        covered = {k for k, r in rows.items() if r.get("module") == key}
        assert covered == set(impl.spec.rows), key
        for row_key, maturity in impl.spec.rows.items():
            assert rows[row_key]["maturity"] == maturity.value, row_key
            assert impl.__name__ in rows[row_key]["ours"], row_key
    assert all(r.get("module") in IMPLEMENTATIONS for r in rows.values() if r.get("module"))
    decidable = {r["module"] for r in catalog()["modules"] if r["decidable"]}
    assert decidable == set(IMPLEMENTATIONS)


def test_ledger_doc_is_rendered_from_the_json() -> None:
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "render_ledger.py"), "--check"], capture_output=True,
                            text=True, check=False)
    assert result.returncode == 0, result.stdout


def test_not_modeled_and_unknown_modules_are_refused(after_q1: svc.Session) -> None:
    with pytest.raises(ModuleDecisionError, match="not-modeled"):
        preview(after_q1, {"production.quality": {"inspection": 1}})
    with pytest.raises(ModuleDecisionError, match="unknown business module"):
        preview(after_q1, {"no.such.module": {}})
    with pytest.raises(ModuleDecisionError, match="decided under"):
        preview(after_q1, {"sales_force.staffing": {}})


def test_without_modules_nothing_changes(after_q1: svc.Session) -> None:
    plain = preview(after_q1, {})
    assert plain["units_demanded[Alpha-1]"]["level"] == "literature"
    assert not any(k.startswith(("sales_force_", "media_mix", "selling_effort", "inventory_", "purchasing_")) for k in plain)
    chain = [c["metric"] for c in plain["cash_end"]["chain"]]
    assert not any(m.startswith(("sales_force_", "inventory_", "purchasing_")) for m in chain)


def test_pack_override_and_unknown_coefficient() -> None:
    pack = dataclasses.replace(PACK, modules={"sales_force": {"force_reference": 4}})
    assert coefficients(pack, "sales_force")["force_reference"] == 4
    with pytest.raises(ValueError, match="unknown coefficient"):
        coefficients(dataclasses.replace(PACK, modules={"sales_force": {"made_up": 1}}), "sales_force")


def test_literature_coefficients_are_inside_their_published_ranges() -> None:
    for key, entry in defaults().items():
        for name, (low, high) in entry.get("ranges", {}).items():
            assert low <= entry["coefficients"][name] <= high, (key, name)
            basis = entry["basis"][name]
            assert basis["kind"] == "literature" and basis["sources"], (key, name)
    # the engine refuses an override outside the range
    with pytest.raises(ValueError, match="outside its literature range"):
        SalesForceModule({**coefficients(PACK, "sales_force"), "selling_elasticity": 0.9})
    with pytest.raises(ValueError, match="outside its literature range"):
        InventoryModule({**coefficients(PACK, "supply.inventory"), "annual_holding_rate": 0.9})
    # the advertising elasticity the media split uses is the demand chain's, inside its own literature range
    demand = json.loads((ROOT / "data" / "demand_literature.json").read_text(encoding="utf-8"))
    low, high = demand["basis"]["ad_elasticity"]["range"]
    assert low <= demand["coefficients"]["ad_elasticity"] <= high


# --- marketing: media mix (literature) ----------------------------------------------------------------------------

WEIGHTS = coefficients(PACK, "marketing.media_mix")["media_weights"]


def parts(shares: dict[str, float]) -> tuple[tuple[str, float, float], ...]:
    total = sum(shares.values())
    return tuple((m, shares.get(m, 0.0) / total, w) for m, w in WEIGHTS.items())


def test_media_split_keeps_the_literature_response_at_the_best_split_and_loses_elsewhere() -> None:
    assert effective_ratio(0.7, (("all", 1.0, 1.0),)) == pytest.approx(0.7)  # one medium = the single curve
    for r in (0.1, 1.0, 5.0):
        best = effective_ratio(r, parts(dict(WEIGHTS)))
        assert best == pytest.approx(r)
        assert effective_ratio(r, parts({"local": 1})) < effective_ratio(r, parts({"local": 1, "regional": 1})) < best
    assert mix_index({m: w for m, w in WEIGHTS.items()}, WEIGHTS) == pytest.approx(1.0)
    assert mix_index({"local": 1.0}, WEIGHTS) < 1.0


def test_each_medium_has_diminishing_returns() -> None:
    grid = [effective_ratio(r, (("local", 1.0, 0.25),)) for r in (0, 1, 2, 3, 4)]
    gains = [b - a for a, b in pairwise(grid)]
    assert all(g > 0 for g in gains) and all(b < a for a, b in pairwise(gains))


def test_more_advertising_raises_demand_with_diminishing_returns(after_q1: svc.Session) -> None:
    mix = {"marketing.media_mix": {"mix": {"Alpha-1": {"local": 1, "regional": 1, "social": 1}}}}
    budgets = [0, 10000, 20000, 40000, 80000, 160000]
    units = [preview(after_q1, mix, advertising=b)["units_demanded[Alpha-1]"]["value"] for b in budgets]
    assert all(b > a for a, b in pairwise(units)), units
    steps = [(units[i + 1] - units[i]) / (budgets[i + 1] - budgets[i]) for i in range(1, len(units) - 1)]
    assert all(b < a for a, b in pairwise(steps)), steps


def test_media_mix_is_literature_level_and_best_split_matches_no_split(after_q1: svc.Session) -> None:
    plain = preview(after_q1, {})
    best = preview(after_q1, {"marketing.media_mix": {"mix": {"Alpha-1": dict(WEIGHTS)}}})
    one = preview(after_q1, {"marketing.media_mix": {"mix": {"Alpha-1": {"search": 1}}}})
    assert best["units_demanded[Alpha-1]"]["value"] == pytest.approx(plain["units_demanded[Alpha-1]"]["value"], rel=1e-9)
    assert one["units_demanded[Alpha-1]"]["value"] < best["units_demanded[Alpha-1]"]["value"]
    for key in DEMAND_CHAIN:
        assert one[key]["level"] == "literature", key  # not downgraded to practice: the form is published
    assert one["media_mix_index[Alpha-1]"]["level"] == "literature"
    assert one["advertising"]["level"] == "verified"
    with pytest.raises(ModuleDecisionError):
        MediaMixLiterature(coefficients(PACK, "marketing.media_mix")).shares({"billboard": 1})


# --- sales force: staffing literature, training / pay / costs heuristic -------------------------------------------

def sales() -> SalesForceModule:
    return SalesForceModule(coefficients(PACK, "sales_force"))


def test_selling_effort_is_a_constant_elasticity_response_with_diminishing_returns() -> None:
    m = sales()
    assert m.effort(0, 0, 3) == 1.0
    efforts = [m.effort(n, 0.0, 1) for n in (0, 2, 4, 8, 16, 32)]
    assert all(b > a for a, b in pairwise(efforts))
    per_person = [m.effort(n + 1, 0.0, 1) - m.effort(n, 0.0, 1) for n in range(0, 40, 4)]
    assert all(b < a for a, b in pairwise(per_person))
    # elasticity with respect to (1 + force / reference) is the coefficient itself
    x1, x2 = 1 + 6 / m.c["force_reference"], 1 + 7 / m.c["force_reference"]
    slope = math.log(m.effort(7, 0, 1) / m.effort(6, 0, 1)) / math.log(x2 / x1)
    assert slope == pytest.approx(m.c["selling_elasticity"])
    assert m.effort(8, 1.0, 1) > m.effort(8, 0.0, 1)  # trained people sell more (heuristic part)


def test_pay_lowers_turnover_within_bounds_and_skill_decays() -> None:
    m = sales()
    rates = [m.quit_rate(s, 3) for s in (0, 3000, 6000, 12000, 1e9)]
    assert all(b <= a for a, b in pairwise(rates)) and rates[0] > rates[2] > rates[3]
    assert all(m.c["min_quit"] <= r <= m.c["max_quit"] for r in rates)
    skills = [m.skill_after(0.0, t) for t in (0, 500, 1000, 2000, 1e9)]
    assert skills[0] == 0 and all(b > a for a, b in pairwise(skills)) and skills[-1] <= 1.0
    assert m.skill_after(0.8, 0) < 0.8


def test_levels_follow_the_part_used(after_q1: svc.Session) -> None:
    hired = preview(after_q1, {"sales_force": {"headcount": 8}})
    for key in DEMAND_CHAIN:
        assert hired[key]["level"] == "literature", key  # staffing alone: published form
    assert hired["selling_effort"]["level"] == "literature"
    assert hired["sales_force_salaries"]["level"] == "heuristic"
    assert hired["cash_end"]["level"] == "heuristic"  # paid with a practice cost rule
    trained = preview(after_q1, {"sales_force": {"headcount": 8, "training": 1000}})
    for key in DEMAND_CHAIN:
        assert trained[key]["level"] == "heuristic", key


def test_more_salespeople_raise_demand_and_cost_more(after_q1: svc.Session) -> None:
    runs = [preview(after_q1, {"sales_force": {"headcount": n}}) for n in (0, 4, 8, 16, 64)]
    units = [r["units_demanded[Alpha-1]"]["value"] for r in runs]
    assert all(b > a for a, b in pairwise(units)), units
    salaries = [r["sales_force_salaries"]["value"] for r in runs]
    assert all(b > a for a, b in pairwise(salaries))


def test_extreme_sales_force_inputs_stay_finite(after_q1: svc.Session) -> None:
    lines = preview(after_q1, {"sales_force": {"headcount": 200, "salary": 600000, "commission_pct": 50, "training": 600000}})
    assert all(math.isfinite(v["value"]) for v in lines.values())
    for bad in ({"headcount": -1}, {"headcount": 201}, {"commission_pct": 51}, {"salary": "lots"}):
        with pytest.raises(ModuleDecisionError):
            preview(after_q1, {"sales_force": bad})


def test_sales_force_carries_over_and_carried_quarters_are_heuristic() -> None:
    runs = three_quarters({"sales_force": {"headcount": 10, "salary": 3000}})
    (_, _), (hired, _), (_, q3) = runs
    assert 0 < hired.module_state["sales_force"]["headcount"] < 10  # some people quit after the quarter
    assert q3.lines["sales_force_salaries"].value > 0  # still employed and paid
    assert q3.lines["units_demanded[Alpha-1]"].level.label == "heuristic"  # carried headcount after (heuristic) quits
    well_paid = three_quarters({"sales_force": {"headcount": 10, "salary": 12000}})[1][0]
    assert well_paid.module_state["sales_force"]["headcount"] > hired.module_state["sales_force"]["headcount"]
    gone = three_quarters({"sales_force": {"headcount": 10}}, {"sales_force": {"headcount": 0}})[2][0]
    assert "sales_force" not in gone.module_state


def test_state_round_trips_through_a_save() -> None:
    state = CompanyState.initial(PACK)
    state.module_state = {"sales_force": {"headcount": 3.5, "skill": 0.2, "salary": 6000, "commission_pct": 3}}
    assert CompanyState.from_dict(json.loads(json.dumps(state.to_dict()))).module_state == state.module_state
    old_save = state.to_dict()
    del old_save["module_state"]
    assert CompanyState.from_dict(old_save).module_state == {}


# --- supply: inventory (holding literature, sell-off heuristic) -------------------------------------------------------

def test_holding_cost_is_rate_times_value_of_what_is_left() -> None:
    (_, _), (state, report), _ = three_quarters({"supply.inventory": {}})
    rate = coefficients(PACK, "supply.inventory")["annual_holding_rate"] / 4
    unit = {b: report.lines[f"unit_cost[{b}]"].value for b in ("Alpha-1", "Gamma-1")}
    expected = sum(units * unit[b] * rate for b, units in state.inventory.items() if units > 0)
    assert report.lines["inventory_holding_cost"].value == pytest.approx(expected)
    assert report.lines["inventory_holding_cost"].level.label == "placeholder"  # valued at a placeholder unit cost
    assert report.lines["units_demanded[Alpha-1]"].level.label == "literature"  # demand untouched


def test_more_left_over_costs_more_to_hold(after_q1: svc.Session) -> None:
    costs = [preview(after_q1, {"supply.inventory": {}}, production=p)["inventory_holding_cost"]["value"] for p in (0, 900, 1100)]
    assert costs[0] <= costs[1] < costs[2]


def test_sell_off_releases_units_for_salvage_and_is_practice() -> None:
    (_, _), (q2_state, _), _ = three_quarters({})
    brand, carried = max(q2_state.inventory.items(), key=lambda kv: kv[1])
    assert carried > 0
    q3 = _plan(svc.SYNTHETIC_PLANS / "q3.yaml")
    after, report = advance(q2_state, Plan.from_dict({**q3, "modules": {"supply.inventory": {"sell_off": {brand: carried / 2}}}}),
                            PACK)
    plain_after, _ = advance(q2_state, Plan.from_dict(q3), PACK)
    salvage = coefficients(PACK, "supply.inventory")["salvage_fraction"]
    unit = report.lines[f"unit_cost[{brand}]"].value
    assert report.lines["inventory_selloff_proceeds"].value == pytest.approx(carried / 2 * salvage * unit)
    assert report.lines["inventory_selloff_proceeds"].level.label == "heuristic"
    assert after.inventory[brand] <= plain_after.inventory[brand]  # fewer units left after a sell-off
    if f"units_sold[{brand}]" in report.lines:
        assert report.lines[f"units_sold[{brand}]"].level.label == "heuristic"
    assert report.lines["cash_end"].level.label == "heuristic"
    with pytest.raises(ModuleDecisionError, match="cannot sell off"):
        advance(q2_state, Plan.from_dict({**q3, "modules": {"supply.inventory": {"sell_off": {brand: carried + 1}}}}), PACK)


# --- supply: purchasing (heuristic) ----------------------------------------------------------------------------------

def test_discount_rises_with_commitment_and_shortfall_costs() -> None:
    m = PurchasingHeuristic(coefficients(PACK, "supply.purchasing"))
    ds = [m.discount(u) for u in (0, 300, 600, 1200, 10**6)]
    assert all(b >= a for a, b in pairwise(ds)) and ds[0] == 0 and ds[-1] < 1


def test_purchasing_lowers_unit_cost_and_marks_cost_not_demand(after_q1: svc.Session) -> None:
    plain = preview(after_q1, {})
    deal = preview(after_q1, {"supply.purchasing": {"contract_units": 800}})
    assert deal["unit_cost[Alpha-1]"]["value"] < plain["unit_cost[Alpha-1]"]["value"]
    assert deal["unit_cost[Alpha-1]"]["level"] == "heuristic" and deal["production_cost"]["level"] == "heuristic"
    assert deal["cash_end"]["level"] == "heuristic"
    assert deal["units_demanded[Alpha-1]"]["level"] == "literature"  # purchasing does not touch demand
    over = preview(after_q1, {"supply.purchasing": {"contract_units": 5000}})
    assert over["purchasing_shortfall_fee"]["value"] > 0
    assert deal["purchasing_shortfall_fee"]["value"] == 0


def test_api_lists_modules() -> None:
    from fastapi.testclient import TestClient

    from marketplace_sim.api.app import create_app

    body = TestClient(create_app(svc.Session())).get("/api/modules").json()
    by_key = {r["key"]: r for r in body["modules"]}
    assert by_key["sales_force.staffing"]["decidable"] is True and by_key["sales_force.staffing"]["module"] == "sales_force"
    assert by_key["supply.inventory_holding"]["ranges"]["annual_holding_rate"]
    assert by_key["production.quality"]["decidable"] is False
    assert body["history"] and body["is_private"] is False
