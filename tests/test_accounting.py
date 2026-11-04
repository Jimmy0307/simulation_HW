"""Accounting rules: the cash-flow identity (verified), structural zeros, and what stays below verified.

The identity is checked with zero residual on every run. Each engine cash row maps to a row of the game's cash-flow
statement with the same effective sign; when the private capture is present its measured structure is checked too
(structure only: row ids and signs, never values).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from marketplace_sim.api import service as svc
from marketplace_sim.api.export import DEMO_QUARTERS, _plan
from marketplace_sim.engine import CompanyState, Plan, Report, advance
from marketplace_sim.pack import load_pack
from marketplace_sim.provenance import Level

ROOT = Path(__file__).resolve().parents[1]
PACK = load_pack(ROOT / "examples" / "synthetic")
STATEMENT = (ROOT / "evidence" / "private" / "extracted" / "nested" / "marketplace-har" / "marketplace-har" / "out" / "q1"
             / "services" / "ProFormaCashFlow.json")

# Engine line -> (game cash-flow row, effective sign). Rows we do not model are zero in the engine.
CASH_ROWS: dict[str, tuple[str, int]] = {
    "revenue": ("sales", +1),
    "production_cost": ("production", -1),
    "advertising": ("advertising", -1),
    "store_setup": ("so", -1),
    "web_center_setup": ("so", -1),
    "outlet_lease": ("so", -1),
    "sales_force_salaries": ("sf", -1),
    "sales_force_hiring": ("sf", -1),
    "sales_force_training": ("sf", -1),
    "sales_force_commission": ("sf", -1),
    "income_tax": ("income_taxes", -1),
    "cd_interest": ("interest_income", +1),
    "inventory_selloff_proceeds": ("other_income", +1),
    "inventory_holding_cost": ("other_exp", -1),
    "purchasing_shortfall_fee": ("other_exp", -1),
    "capex_capacity": ("fixed_cap", -1),
    "stock_raised": ("inc_comm", +1),
    "emergency_loan": ("inc_emer_l", +1),
}
# design_cost has no confirmed row (R&D or production): one reason it stays heuristic. Mapped as an outflow.
UNCONFIRMED = {"design_cost": -1}


def identity_residual(plan: Plan, report: Report) -> float:
    lines = report.lines
    flows = sum(sign * lines[k].value for k, (_row, sign) in CASH_ROWS.items() if k in lines)
    flows += sum(sign * lines[k].value for k, sign in UNCONFIRMED.items() if k in lines)
    flows += plan.cd_withdraw - plan.cd_deposit  # rep_cd (+) and inc_cd (-)
    return float(lines["cash_start"].value + flows - lines["cash_end"].value)


def every_run() -> list[tuple[Plan, Report]]:
    out = []
    plans = [Plan.from_dict(_plan(svc.SYNTHETIC_PLANS / q)) for q in DEMO_QUARTERS]
    variants: list[dict[str, Any]] = [{}, {"sales_force": {"headcount": 6, "training": 900}},
                                      {"supply.inventory": {}, "supply.purchasing": {"contract_units": 700}},
                                      {"marketing.media_mix": {"mix": {"Alpha-1": {"local": 1, "search": 3}}}}]
    for modules in variants:
        state = CompanyState.initial(PACK)
        for plan in plans:
            plan = copy.deepcopy(plan)
            plan.modules = modules if plan.brands and any(b.price > 0 for b in plan.brands) else {}
            state, report = advance(state, plan, PACK)
            out.append((plan, report))
    return out


def test_cash_identity_has_zero_residual_on_every_run() -> None:
    runs = every_run()
    assert len(runs) == 12
    for plan, report in runs:
        assert identity_residual(plan, report) == pytest.approx(0.0, abs=1e-6), report.quarter
    # every cash-relevant line of every run is mapped (nothing flows into cash unaccounted)
    seen = {k for _, r in runs for k in r.lines}
    assert {"sales_force_salaries", "inventory_holding_cost", "purchasing_shortfall_fee"} <= seen


@pytest.mark.skipif(not STATEMENT.exists(), reason="no private capture")
def test_mapping_matches_the_captured_statement_structure() -> None:
    data = json.loads(STATEMENT.read_text(encoding="utf-8"))["staticData"]
    sign = {item["id"]: int(section["sign"]) * int(item["sign"]) for section in data["sections"] for item in section["items"]}
    for line, (row, expected) in CASH_ROWS.items():
        assert row in sign, row
        assert sign[row] == expected, (line, row)
    assert sign["inc_cd"] == -1 and sign["rep_cd"] == +1


def setup_quarter() -> Plan:
    """A quarter with only verified decisions: raise equity, buy capacity, open stores, deposit in a CD."""
    return Plan.from_dict({"stock_issue": [{"shares": 1000, "price": 10}], "capacity_increase": max(o.units for o in PACK.capacity_options),
                           "open_stores": [PACK.stores[0].key], "cd": {"deposit": 5000}})


def test_structural_zeros_make_a_setup_quarter_verified() -> None:
    _, report = advance(CompanyState.initial(PACK), setup_quarter(), PACK)
    lines = report.lines
    for key in ("outlet_lease", "design_cost", "production_cost", "revenue", "income_tax"):
        assert lines[key].level == Level.VERIFIED and lines[key].value == 0.0, key
    # stock raised is a derived identity, so the loan zero and ending cash are trusted at derived level: shown plain
    assert lines["emergency_loan"].level >= Level.DERIVED and lines["emergency_loan"].value == 0.0
    assert lines["cash_end"].level >= Level.DERIVED
    # profit lines are a cash-basis statement, the game's is accrual: never above placeholder
    assert lines["operating_profit_before_tax"].level == Level.PLACEHOLDER
    assert lines["net_income"].level == Level.PLACEHOLDER
    # market lines stay at the demand model's level (rivals still sell)
    assert lines["market_units_total"].level == Level.LITERATURE


def test_unverified_branches_stay_placeholder() -> None:
    state, _ = advance(CompanyState.initial(PACK), setup_quarter(), PACK)
    plan = Plan.from_dict({"brands": [{"name": "B", "brand_type": PACK.brand_types[0].code, "price": 500, "production": 50}]})
    _, report = advance(state, plan, PACK)
    lines = report.lines
    assert lines["outlet_lease"].level == Level.PLACEHOLDER  # a store was open at quarter start: timing unverified
    assert lines["design_cost"].level == Level.PLACEHOLDER  # a brand was designed
    assert lines["production_cost"].level == Level.PLACEHOLDER  # units were produced
    assert lines["income_tax"].level == Level.PLACEHOLDER  # something was produced: accrual income may differ
    assert lines["cash_end"].level <= Level.PLACEHOLDER


def test_tax_and_loan_zero_follow_the_certainty_of_their_sign() -> None:
    from marketplace_sim import modules as m
    from marketplace_sim.provenance import Tagged

    loss_lit = Tagged(-10.0, Level.LITERATURE, "x")
    assert m.income_tax(PACK, loss_lit, inventory_free=True).level == Level.LITERATURE
    assert m.income_tax(PACK, loss_lit, inventory_free=False).level == Level.PLACEHOLDER
    assert m.income_tax(PACK, Tagged(10.0, Level.VERIFIED, "x"), inventory_free=True).level == Level.PLACEHOLDER
    assert m.emergency_loan(Tagged(5.0, Level.VERIFIED, "x")).level == Level.VERIFIED
    assert m.emergency_loan(Tagged(-5.0, Level.VERIFIED, "x")).level == Level.PLACEHOLDER
    assert m.emergency_loan(Tagged(-5.0, Level.VERIFIED, "x")).value == 5.0


def test_values_did_not_change_only_levels() -> None:
    """The structural-zero branches change levels, never values (same rule, same arithmetic)."""
    from marketplace_sim import modules as m
    from marketplace_sim.provenance import Tagged

    for pretax in (-5.0, 0.0, 5.0):
        for free in (True, False):
            assert m.income_tax(PACK, Tagged(pretax, Level.VERIFIED, "x"), inventory_free=free).value == \
                max(pretax, 0.0) * PACK.finance.get("tax_rate_percent", 0.0) / 100
    assert m.recurring_lease(PACK.stores, set()).value == 0.0
    assert m.design_cost(PACK, 0).value == 0.0
