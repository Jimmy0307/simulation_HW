"""Business modules: framework, ledger consistency, and SANITY tests of the two heuristic modules.

These are not accuracy tests. Heuristic rules have no calibration; the tests only check direction, monotonicity,
diminishing returns, bounds at extreme inputs, and that every number downstream is labelled heuristic.
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
from marketplace_sim.business.marketing import MediaMixHeuristic
from marketplace_sim.business.registry import coefficients
from marketplace_sim.business.sales_force import SalesForceHeuristic
from marketplace_sim.engine import CompanyState, Plan, advance
from marketplace_sim.pack import load_pack

ROOT = Path(__file__).resolve().parents[1]
PACK = load_pack(ROOT / "examples" / "synthetic")
DOWNSTREAM = ("units_demanded[Alpha-1]", "units_sold[Alpha-1]", "market_share", "market_units_total", "revenue",
              "net_income", "cash_end")


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


# --- ledger and framework ---------------------------------------------------------------------------------------------

def test_ledger_rows_are_complete_and_consistent() -> None:
    rows = ledger_rows()
    keys = [r["key"] for r in rows]
    assert len(keys) == len(set(keys))
    areas = {a["id"] for a in json.loads((ROOT / "data" / "modeling_ledger.json").read_text(encoding="utf-8"))["areas"]}
    sources = json.loads((ROOT / "data" / "modeling_ledger.json").read_text(encoding="utf-8"))["sources"]
    for row in rows:
        assert row["maturity"] in {m.value for m in Maturity}, row["key"]
        assert row["real_status"] in {"measured", "inferred", "unknown"}, row["key"]
        assert row["area"] in areas and row["next_step"] and row["capture"], row["key"]
        assert set(row["sources"]) <= set(sources), row["key"]
        if row["real_status"] != "measured":  # anything not captured is explicitly unverified
            assert "unverified" in row["capture"] or "unknown" in row["capture"], row["key"]
    # the seven areas the brief asks for are all covered
    assert {"marketing", "sales_force", "production", "supply", "rnd", "finance", "strategy"} <= {r["area"] for r in rows}


def test_every_implementation_matches_its_ledger_row() -> None:
    rows = ledger_rows()
    for key, impl in IMPLEMENTATIONS.items():
        covered = [r for r in rows if r.get("module") == key]
        assert covered, f"{key} has no ledger row"
        assert all(r["maturity"] == impl.spec.maturity.value for r in covered), key
        assert all(impl.__name__ in r["ours"] for r in covered), key
    assert all(r.get("module") in IMPLEMENTATIONS for r in rows if "module" in r)
    assert {r["key"] for r in rows if r.get("module") == "sales_force"} == {
        "sales_force.staffing", "sales_force.compensation", "sales_force.training"}
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


def test_without_modules_nothing_changes(after_q1: svc.Session) -> None:
    plain = preview(after_q1, {})
    assert plain["units_demanded[Alpha-1]"]["level"] == "literature"
    assert not any(k.startswith(("sales_force_", "ad_efficiency", "selling_effort")) for k in plain)
    chain = [c["metric"] for c in plain["cash_end"]["chain"]]
    assert not any(m.startswith("sales_force_") for m in chain)  # an inactive module is not in any source chain


def test_pack_override_and_unknown_coefficient() -> None:
    pack = dataclasses.replace(PACK, modules={"sales_force": {"max_lift": 0.2}})
    assert coefficients(pack, "sales_force")["max_lift"] == 0.2
    with pytest.raises(ValueError, match="unknown coefficient"):
        coefficients(dataclasses.replace(PACK, modules={"sales_force": {"made_up": 1}}), "sales_force")


# --- marketing: media mix (heuristic) ---------------------------------------------------------------------------------

def mix_module() -> MediaMixHeuristic:
    return MediaMixHeuristic(coefficients(PACK, "marketing.media_mix"))


def test_media_mix_efficiency_is_bounded_and_rewards_spreading() -> None:
    module = mix_module()
    weights = module.weights
    best = module.efficiency({m: w * w for m, w in weights.items()})
    assert best == pytest.approx(1.0)
    single = module.efficiency({"local": 1})
    two = module.efficiency({"local": 1, "regional": 1})
    assert 0 < single < two < best <= 1.0 + 1e-12
    assert module.efficiency({"local": 2, "social": 2}) == pytest.approx(module.efficiency({"local": 1, "social": 1}))
    with pytest.raises(ModuleDecisionError):
        module.efficiency({"local": 0})
    with pytest.raises(ModuleDecisionError):
        module.efficiency({"billboard": 1})


def test_more_advertising_raises_demand_with_diminishing_returns(after_q1: svc.Session) -> None:
    mix = {"marketing.media_mix": {"mix": {"Alpha-1": {"local": 1, "regional": 1, "social": 1}}}}
    budgets = [0, 10000, 20000, 40000, 80000, 160000]
    units = [preview(after_q1, mix, advertising=b)["units_demanded[Alpha-1]"]["value"] for b in budgets]
    assert all(b > a for a, b in itertools.pairwise(units)), units
    steps = [(units[i + 1] - units[i]) / (budgets[i + 1] - budgets[i]) for i in range(1, len(units) - 1)]
    assert all(b < a for a, b in itertools.pairwise(steps)), steps  # marginal effect falls


def test_better_mix_beats_one_medium_at_the_same_budget(after_q1: svc.Session) -> None:
    one = preview(after_q1, {"marketing.media_mix": {"mix": {"Alpha-1": {"search": 1}}}})
    spread = preview(after_q1, {"marketing.media_mix": {"mix": {"Alpha-1": {"local": 1, "regional": 0.8,
                                                                                 "social": 0.6, "search": 0.5}}}})
    assert spread["units_demanded[Alpha-1]"]["value"] > one["units_demanded[Alpha-1]"]["value"]
    assert spread["advertising"]["value"] == one["advertising"]["value"]  # same spend


def test_media_mix_marks_everything_downstream_heuristic(after_q1: svc.Session) -> None:
    lines = preview(after_q1, {"marketing.media_mix": {"mix": {"Alpha-1": {"local": 1}}}})
    for key in (*DOWNSTREAM, "ad_efficiency[Alpha-1]", "effective_advertising[Alpha-1]"):
        assert lines[key]["level"] == "heuristic" and lines[key]["uncalibrated"] is True, key
    assert any(k.startswith("rival_share[") and v["level"] == "heuristic" for k, v in lines.items())
    assert lines["advertising"]["level"] == "verified"  # the spend itself is a plan input
    assert lines["store_setup"]["level"] == "verified"  # cost lines outside the demand chain keep their level


# --- sales force (heuristic) ------------------------------------------------------------------------------------------

def sales_module() -> SalesForceHeuristic:
    return SalesForceHeuristic(coefficients(PACK, "sales_force"))


def test_effort_rises_with_headcount_and_training_with_diminishing_returns() -> None:
    m = sales_module()
    efforts = [m.effort(n, 0.0, 3) for n in (0, 2, 4, 8, 16, 32, 1000)]
    assert efforts[0] == 1.0
    assert all(b > a for a, b in itertools.pairwise(efforts))
    per_person = [m.effort(n + 1, 0.0, 3) - m.effort(n, 0.0, 3) for n in range(0, 40, 4)]
    assert all(b < a for a, b in itertools.pairwise(per_person))  # each extra person adds less
    assert efforts[-1] <= 1 + m.c["max_lift"] + 1e-12  # ceiling
    assert m.effort(8, 1.0, 3) > m.effort(8, 0.0, 3)  # trained people sell more
    skills = [m.skill_after(0.0, t) for t in (0, 500, 1000, 2000, 4000, 1e9)]
    assert skills[0] == 0 and all(b > a for a, b in itertools.pairwise(skills)) and skills[-1] <= 1.0
    assert m.skill_after(0.8, 0) < 0.8  # skill decays without training


def test_pay_lowers_turnover_within_bounds() -> None:
    m = sales_module()
    rates = [m.quit_rate(s, 3) for s in (0, 3000, 6000, 12000, 1e9)]
    assert all(b <= a for a, b in itertools.pairwise(rates)) and rates[0] > rates[2] > rates[3]
    assert all(m.c["min_quit"] <= r <= m.c["max_quit"] for r in rates)
    assert m.quit_rate(6000, 10) < m.quit_rate(6000, 0)  # commission counts as pay


def test_more_salespeople_raise_demand_and_cost_more(after_q1: svc.Session) -> None:
    runs = [preview(after_q1, {"sales_force": {"headcount": n}}) for n in (0, 4, 8, 16, 64)]
    units = [r["units_demanded[Alpha-1]"]["value"] for r in runs]
    assert all(b > a for a, b in itertools.pairwise(units)), units
    salaries = [r["sales_force_salaries"]["value"] for r in runs]
    assert all(b > a for a, b in itertools.pairwise(salaries))
    gain_small, gain_big = units[1] - units[0], (units[4] - units[3]) / 12  # per person, 0->4 vs 16->64
    assert gain_big < gain_small / 4


def test_extreme_sales_force_inputs_stay_finite(after_q1: svc.Session) -> None:
    lines = preview(after_q1, {"sales_force": {"headcount": 200, "salary": 600000, "commission_pct": 50,
                                               "training": 600000}})
    assert all(math.isfinite(v["value"]) for v in lines.values())
    assert lines["selling_effort"]["value"] <= 1 + sales_module().c["max_lift"] + 1e-12
    for bad in ({"headcount": -1}, {"headcount": 201}, {"commission_pct": 51}, {"salary": "lots"}):
        with pytest.raises(ModuleDecisionError):
            preview(after_q1, {"sales_force": bad})


def test_sales_force_marks_downstream_and_carries_over() -> None:
    state = CompanyState.initial(PACK)
    q1 = Plan.from_dict(_plan(svc.SYNTHETIC_PLANS / "q1.yaml"))
    state, _ = advance(state, q1, PACK)
    q2 = _plan(svc.SYNTHETIC_PLANS / "q2.yaml")
    hired, report = advance(state, Plan.from_dict({**q2, "modules": {"sales_force": {"headcount": 10, "salary": 3000}}}),
                            PACK)
    for key in (*DOWNSTREAM, "sales_force_salaries", "selling_effort"):
        assert report.lines[key].level.label == "heuristic", key
    carried = hired.module_state["sales_force"]
    assert 0 < carried["headcount"] < 10  # some people quit after the quarter
    low_pay = carried["headcount"]
    well_paid, _ = advance(state, Plan.from_dict({**q2, "modules": {"sales_force": {"headcount": 10, "salary": 12000}}}),
                           PACK)
    assert well_paid.module_state["sales_force"]["headcount"] > low_pay  # better pay keeps more people
    # next quarter without a sales_force block: the people are still employed, paid, and still mark the numbers
    q3 = Plan.from_dict(_plan(svc.SYNTHETIC_PLANS / "q3.yaml"))
    after, report3 = advance(hired, q3, PACK)
    assert report3.lines["sales_force_salaries"].value > 0 and report3.lines["cash_end"].level.label == "heuristic"
    # letting everyone go stops the module (and its marking) from the following quarter
    gone, _ = advance(after, Plan.from_dict({**_plan(svc.SYNTHETIC_PLANS / "q3.yaml"),
                                              "modules": {"sales_force": {"headcount": 0}}}), PACK)
    assert "sales_force" not in gone.module_state
    _, clean = advance(gone, q3, PACK)
    assert clean.lines["units_demanded[Alpha-1]"].level.label == "literature"  # demand is clean again
    assert clean.lines["cash_end"].level.label == "heuristic"  # but cash carried from a heuristic quarter stays so


def test_state_round_trips_through_a_save() -> None:
    state = CompanyState.initial(PACK)
    state.module_state = {"sales_force": {"headcount": 3.5, "skill": 0.2, "salary": 6000, "commission_pct": 3}}
    assert CompanyState.from_dict(json.loads(json.dumps(state.to_dict()))).module_state == state.module_state
    old_save = state.to_dict()
    del old_save["module_state"]
    assert CompanyState.from_dict(old_save).module_state == {}  # saves from before this field still load


def test_api_lists_modules() -> None:
    from fastapi.testclient import TestClient

    from marketplace_sim.api.app import create_app

    body = TestClient(create_app(svc.Session())).get("/api/modules").json()
    assert body["counts"]["heuristic"] >= 2 and body["counts"]["not-modeled"] >= 1
    by_key = {r["key"]: r for r in body["modules"]}
    assert by_key["sales_force.staffing"]["decidable"] is True and by_key["sales_force.staffing"]["module"] == "sales_force"
    assert by_key["marketing.media_mix"]["decidable"] is True and by_key["production.quality"]["decidable"] is False
    assert body["is_private"] is False
