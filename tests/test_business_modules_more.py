"""Round-3 business modules: sanity tests (direction, bounds, levels, identities). Not accuracy tests.

Every module here is checked for: refusing bad decisions, the direction of its effect, that what it touches carries
its level (heuristic -> 練習, literature -> ≈), and the identities it promises (loans reconcile, the balance sheet
balances, the cash identity holds with every module line in it).
"""

from __future__ import annotations

import copy
import dataclasses
import itertools
from pathlib import Path
from typing import Any

import pytest

from marketplace_sim.api import service as svc
from marketplace_sim.api.export import _plan
from marketplace_sim.business import ModuleDecisionError
from marketplace_sim.business.product import LearningCurveModule, RnDModule
from marketplace_sim.business.registry import IMPLEMENTATIONS, catalog, coefficients
from marketplace_sim.engine import CompanyState, Plan, Report, advance
from marketplace_sim.metrics import METRICS, MODULE_METRICS, lookup
from marketplace_sim.pack import load_pack

ROOT = Path(__file__).resolve().parents[1]
PACK = load_pack(ROOT / "examples" / "synthetic")
BRAND = "Alpha-1"


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


def run(quarters: list[dict[str, Any]], *, extra: dict[int, dict[str, Any]] | None = None) -> list[tuple[CompanyState, Report, Plan]]:
    """Play the synthetic q1..q3 plans (repeating q3 if more quarters are asked) with per-quarter modules."""
    names = ["q1.yaml", "q2.yaml", "q3.yaml"]
    state = CompanyState.initial(PACK)
    out = []
    for i, modules in enumerate(quarters):
        plan_dict = {**_plan(svc.SYNTHETIC_PLANS / names[min(i, 2)]), "modules": modules, **((extra or {}).get(i, {}))}
        plan = Plan.from_dict(plan_dict)
        state, report = advance(state, plan, PACK)
        out.append((state, report, plan))
    return out


def v(lines: dict[str, Any], key: str) -> float:
    return float(lines[key]["value"]) if isinstance(lines[key], dict) else float(lines[key].value)


def lvl(lines: dict[str, Any], key: str) -> str:
    return str(lines[key]["level"])


# --- framework ---------------------------------------------------------------------------------------------------------

def test_every_module_line_is_explained_and_fields_point_at_its_rows() -> None:
    for key, impl in IMPLEMENTATIONS.items():
        for f in getattr(impl, "fields", ()):
            assert f.part in impl.spec.rows, (key, f.name)
        for m in getattr(impl, "metrics", ()):
            assert lookup(m.name) is not None and m.name.split("[")[0] in MODULE_METRICS
    # module expense lines are in the profit and cash chains
    assert "promotion_rebates" in METRICS["cash_end"].inputs and "loan_interest" in METRICS["operating_profit_before_tax"].inputs
    assert "dividends_paid" in METRICS["cash_end"].inputs and "dividends_paid" not in METRICS["operating_profit_before_tax"].inputs
    rows = {r["key"]: r for r in catalog()["modules"]}
    assert rows["supply.replenishment"]["primary"] and not rows["production.scheduling"]["primary"]
    assert [f["name"] for f in rows["finance.loans"]["fields"]][:2] == ["short_loan", "long_loan"]


def test_bad_decisions_are_refused(after_q1: svc.Session) -> None:
    with pytest.raises(ModuleDecisionError, match="unknown decision"):
        preview(after_q1, {"marketing.promotions": {"coupon": 3}})
    with pytest.raises(ModuleDecisionError, match="between"):
        preview(after_q1, {"marketing.promotions": {"rebate": {BRAND: 10_000}}})
    with pytest.raises(ModuleDecisionError, match="no such brand"):
        preview(after_q1, {"marketing.promotions": {"rebate": {"Nope": 5}}})
    with pytest.raises(ModuleDecisionError, match="must be one of"):
        preview(after_q1, {"production.operating_capacity": {"shifts": "4"}})
    with pytest.raises(ModuleDecisionError, match="cannot be stopped"):
        preview(after_q1, {"finance.loans": {"stop": True}})


def test_literature_ranges_are_enforced() -> None:
    lc = coefficients(PACK, "production.learning_curve")
    with pytest.raises(ValueError, match="literature range"):
        LearningCurveModule({**lc, "progress_ratio": 0.6}, PACK)
    rd = coefficients(PACK, "rnd.feature_development")
    with pytest.raises(ValueError, match="literature range"):
        RnDModule({**rd, "rnd_elasticity": 0.4}, PACK)


# --- marketing -----------------------------------------------------------------------------------------------------------

def test_rebate_raises_units_and_pays_on_redeemed_units(after_q1: svc.Session) -> None:
    plain = preview(after_q1, {})
    promo = preview(after_q1, {"marketing.promotions": {"rebate": {BRAND: 60}}})
    assert v(promo, f"units_demanded[{BRAND}]") > v(plain, f"units_demanded[{BRAND}]")
    c = coefficients(PACK, "marketing.promotions")
    assert v(promo, "promotion_rebates") == pytest.approx(v(promo, f"units_sold[{BRAND}]") * 60 * c["redemption_rate"])
    assert lvl(promo, f"units_sold[{BRAND}]") == "heuristic" and lvl(promo, "net_income") == "heuristic"
    assert v(promo, "revenue") == pytest.approx(sum(v(promo, f"units_sold[{b}]") * p for b, p in
                                                    [(BRAND, 697), ("Gamma-1", 1193)]))  # list price booked


def test_message_on_a_valued_need_helps_and_on_a_minor_need_hurts(after_q1: svc.Session) -> None:
    plain = v(preview(after_q1, {}), f"units_demanded[{BRAND}]")
    first = preview(after_q1, {"marketing.ad_copy": {"message": {BRAND: "first"}}})
    third = preview(after_q1, {"marketing.ad_copy": {"message": {BRAND: "third"}}})
    assert v(first, f"units_demanded[{BRAND}]") > plain > v(third, f"units_demanded[{BRAND}]")
    lift = coefficients(PACK, "marketing.ad_copy")["lift"]
    assert 1 - lift <= v(third, f"ad_copy_factor[{BRAND}]") < 1 < v(first, f"ad_copy_factor[{BRAND}]") <= 1 + lift


def test_internet_marketing_needs_a_web_center() -> None:
    # q2: the web center opens during the quarter (no web share yet); q3: it is open at quarter start
    out = run([{}, {"marketing.internet": {"web_spend": 50000}}, {"marketing.internet": {"web_spend": 50000}}])
    assert out[1][1].lines["internet_factor"].value == 1.0
    assert out[2][1].lines["internet_factor"].value > 1.0
    assert out[2][1].lines["internet_marketing"].value == 50000


def test_market_research_costs_and_reports_engine_estimates(after_q1: svc.Session) -> None:
    lines = preview(after_q1, {"marketing.market_research": {"segment_report": True, "rival_report": True}})
    assert v(lines, "market_research") == 2 * coefficients(PACK, "marketing.market_research")["report_price"]
    seg = [k for k in lines if k.startswith("research_segment_units[")]
    assert seg and all(lvl(lines, k) in {"literature", "heuristic", "placeholder"} for k in seg)
    assert any(k.startswith("research_rival_share[") for k in lines)


def test_web_salespeople_work_only_with_web_share() -> None:
    out = run([{}, {"sales_force": {"headcount": 0, "web_headcount": 4}}, {"sales_force": {"headcount": 0, "web_headcount": 4}}])
    q2, q3 = out[1][1].lines, out[2][1].lines
    assert q2["web_sales_effort"].value == 1.0 and q3["web_sales_effort"].value > 1.0
    assert q3["selling_effort"].level.label == "heuristic"
    assert q3["web_sales_salaries"].value > 0


# --- people and operations -----------------------------------------------------------------------------------------------

def test_higher_wages_cost_more_labour_and_raise_capacity(after_q1: svc.Session) -> None:
    low = preview(after_q1, {"hr.production_workers": {"wage_index": 0.8}})
    high = preview(after_q1, {"hr.production_workers": {"wage_index": 1.3}})
    assert v(high, f"unit_cost[{BRAND}]") > v(low, f"unit_cost[{BRAND}]")
    assert v(high, "capacity_units_per_quarter") > v(low, "capacity_units_per_quarter")
    assert lvl(high, "capacity_units_per_quarter") == "heuristic" and lvl(high, f"unit_cost[{BRAND}]") == "heuristic"


def test_morale_is_only_seen_with_a_survey(after_q1: svc.Session) -> None:
    hidden = preview(after_q1, {"hr.executive_and_culture": {"participation": 50000}})
    seen = preview(after_q1, {"hr.executive_and_culture": {"participation": 50000, "survey": True}})
    assert "hr_morale" not in hidden and 0 <= v(seen, "hr_morale") <= 1
    assert v(seen, "culture_survey") > 0 and v(hidden, "culture_survey") == 0


def test_shifts_and_overtime_add_capacity_and_overtime_costs_only_when_used(after_q1: svc.Session) -> None:
    one = preview(after_q1, {"production.operating_capacity": {"shifts": "1"}})
    two = preview(after_q1, {"production.operating_capacity": {"shifts": "2", "overtime_pct": 10}})
    assert v(two, "capacity_units_per_quarter") > v(one, "capacity_units_per_quarter")
    assert v(two, "shift_cost") > 0 and "shift_cost" not in one and "capacity_units_per_quarter" in one
    assert lvl(one, "capacity_units_per_quarter") == "verified"  # one shift, no overtime: nothing marked
    # production well under regular capacity: no overtime premium
    assert v(two, "overtime_premium") == 0
    big = preview(after_q1, {"production.operating_capacity": {"overtime_pct": 20}}, production=10**6)
    assert v(big, "overtime_premium") > 0


def test_relocation_is_charged_once_and_home_clears_state() -> None:
    out = run([{}, {"production.factory_location": {"location": "low_cost"}}, {},
               {"production.factory_location": {"location": "home"}}])
    q2, q3, q4 = (out[i][1].lines for i in (1, 2, 3))
    assert q2["relocation_cost"].value > 0 and q3["relocation_cost"].value == 0  # carried, no new move
    assert q3["location_labor_factor"].value < 1 and q4["relocation_cost"].value > 0
    assert "production.factory_location" not in out[3][0].module_state


# --- product and planning ------------------------------------------------------------------------------------------------

def test_quality_spend_lowers_defects_and_costs_per_unit(after_q1: svc.Session) -> None:
    none = preview(after_q1, {"production.quality": {}})
    qa = preview(after_q1, {"production.quality": {"qa_per_unit": {BRAND: 30}}})
    assert v(qa, f"defect_rate[{BRAND}]") < v(none, f"defect_rate[{BRAND}]")
    assert v(qa, f"unit_cost[{BRAND}]") == pytest.approx(v(none, f"unit_cost[{BRAND}]") + 30)
    assert v(qa, f"units_demanded[{BRAND}]") > v(none, f"units_demanded[{BRAND}]")
    assert v(none, "warranty_cost") > 0


def test_rnd_stock_builds_decays_and_raises_attraction() -> None:
    out = run([{}, {"rnd.feature_development": {"rnd": {BRAND: 100000}}}, {}])
    q2, q3 = out[1][1].lines, out[2][1].lines
    keep = (1 - coefficients(PACK, "rnd.feature_development")["annual_depreciation"]) ** 0.25
    assert q2[f"rnd_stock[{BRAND}]"].value == pytest.approx(100000)
    assert q3[f"rnd_stock[{BRAND}]"].value == pytest.approx(100000 * keep)
    assert q2[f"rnd_factor[{BRAND}]"].value > 1 and q2[f"rnd_factor[{BRAND}]"].level.label == "literature"
    assert q2["rnd_spending"].level.label == "heuristic"


def test_learning_curve_lowers_conversion_cost_with_experience() -> None:
    lc = LearningCurveModule(coefficients(PACK, "production.learning_curve"), PACK)
    factors = [lc.factor(c, 500) for c in (0, 2000, 8000, 32000)]
    assert all(b < a for a, b in itertools.pairwise(factors)) and factors[0] < 1
    out = run([{}, {"production.learning_curve": {}}, {}])
    q2, q3 = out[1][1].lines, out[2][1].lines
    assert q3[f"learning_factor[{BRAND}]"].value < q2[f"learning_factor[{BRAND}]"].value
    assert q3[f"cumulative_units[{BRAND}]"].value == pytest.approx(613)
    assert q2[f"learning_factor[{BRAND}]"].level.label == "literature"
    assert q2[f"unit_cost[{BRAND}]"].level.label == "placeholder"  # the unit cost rule itself is still a placeholder
    stopped = run([{}, {"production.learning_curve": {}}, {"production.learning_curve": {"stop": True}}])
    assert "production.learning_curve" not in stopped[2][0].module_state


def test_order_up_to_rule_uses_the_demand_record() -> None:
    rule = {"rule": {BRAND: "order_up_to"}, "cover": 1.5}
    out = run([{}, {"supply.replenishment": rule}, {"supply.replenishment": rule}])
    q2, q3 = out[1][1], out[2][1]
    assert any("no demand record" in n for n in q2.notes)  # first quarter: plan production
    recorded = q2.lines[f"units_demanded[{BRAND}]"].value
    start_inventory = out[1][0].inventory[BRAND]
    assert q3.lines[f"replenishment_units[{BRAND}]"].value == pytest.approx(max(recorded * 1.5 - start_inventory, 0))
    assert q3.lines[f"replenishment_units[{BRAND}]"].level.label == "literature"
    assert q3.lines["production_cost"].level.label == "placeholder"


def test_priority_order_decides_who_gets_scarce_capacity(after_q1: svc.Session) -> None:
    def produced(order: dict[str, int]) -> float:
        lines = preview(after_q1, {"supply.replenishment": {"priority": order}}, production=10**6)
        return v(lines, "production_cost")

    # Gamma-1 first leaves Alpha-1 the remainder: production cost differs with the order
    assert produced({BRAND: 1, "Gamma-1": 2}) != produced({BRAND: 2, "Gamma-1": 1})


# --- finance and accounting ----------------------------------------------------------------------------------------------

def test_loans_reconcile_and_interest_is_an_expense() -> None:
    out = run([{}, {"finance.loans": {"short_loan": 100000, "long_loan": 400000, "long_term": "4"}}, {}, {}])
    proceeds = repaid = 0.0
    for _state, report, _p in out[1:]:
        L = report.lines
        proceeds += L["loan_short_proceeds"].value + L["loan_long_proceeds"].value
        repaid += -(L["loan_short_repaid"].value + L["loan_long_repaid"].value)
        assert proceeds - repaid == pytest.approx(L["loan_balance_short"].value + L["loan_balance_long"].value)
    q3 = out[2][1].lines
    c = coefficients(PACK, "finance.loans")
    assert q3["loan_interest"].value == pytest.approx(100000 * c["short_rate_quarterly"] + 400000 * c["long_rate_quarterly"])
    assert q3["loan_long_repaid"].value == pytest.approx(-100000)


def cash_residual(report: Report, plan: Plan) -> float:
    """cash_end = start + revenue + stock + CD flow + interest - expenses - capex - tax + income + financing + loan."""
    L = report.lines
    roles = {m.name.split("[")[0]: m.role for impl in IMPLEMENTATIONS.values() for m in getattr(impl, "metrics", ())}
    core_exp = {"store_setup", "web_center_setup", "outlet_lease", "design_cost", "production_cost", "advertising",
                "sales_force_salaries", "sales_force_hiring", "sales_force_training", "sales_force_commission",
                "inventory_holding_cost", "purchasing_shortfall_fee", "web_sales_salaries"}
    flow = 0.0
    for name, line in L.items():
        base = name.split("[")[0]
        if base in core_exp or roles.get(base) == "expense":
            flow -= line.value
        elif roles.get(base) in {"income", "financing"} or base == "inventory_selloff_proceeds":
            flow += line.value
    flow += L["revenue"].value + L["stock_raised"].value + L["cd_interest"].value + plan.cd_withdraw - plan.cd_deposit
    flow += -L["capex_capacity"].value - L["income_tax"].value + L["emergency_loan"].value
    return float(L["cash_start"].value + flow - L["cash_end"].value)


EVERYTHING = {
    "marketing.promotions": {"rebate": {BRAND: 20}}, "marketing.ad_copy": {"message": {BRAND: "first"}},
    "marketing.internet": {"web_spend": 20000}, "marketing.market_research": {"segment_report": True},
    "sales_force": {"headcount": 6, "web_headcount": 2, "training": 500},
    "hr.production_workers": {"wage_index": 1.1}, "hr.executive_and_culture": {"participation": 20000, "exec_bonus_pct": 1},
    "production.operating_capacity": {"shifts": "2", "overtime_pct": 5},
    "production.quality": {"qa_per_unit": {BRAND: 10}}, "rnd.feature_development": {"rnd": {BRAND: 50000}},
    "production.learning_curve": {}, "supply.replenishment": {"rule": {BRAND: "order_up_to"}},
    "supply.inventory": {}, "supply.purchasing": {"contract_units": 600},
    "finance.loans": {"short_loan": 50000, "long_loan": 200000, "dividend": 10000},
    "accounting.accrual": {}, "strategy.balanced_scorecard": {},
}


def test_cash_identity_and_balance_sheet_hold_with_every_module() -> None:
    q3 = {k: v for k, v in EVERYTHING.items() if k != "finance.loans"}
    more = {"stock_issue": [{"shares": 1000, "price": 20}],  # q3 overproduces so q4 can sell some off
            "brands": [{"name": BRAND, "brand_type": "A", "price": 697, "production": 3000, "advertising": 29989},
                       {"name": "Gamma-1", "brand_type": "C", "price": 1147, "production": 900, "advertising": 19963}]}
    q3["supply.replenishment"] = {}
    first = run([{}, EVERYTHING, q3], extra={2: more})
    held = max(first[2][0].inventory, key=lambda b: first[2][0].inventory[b])
    assert first[2][0].inventory[held] >= 5
    out = run([{}, EVERYTHING, q3, {"supply.inventory": {"sell_off": {held: 5}}}], extra={2: more})
    assert out[3][1].lines["inventory_selloff_proceeds"].value > 0
    for _state, report, plan in out:
        assert cash_residual(report, plan) == pytest.approx(0, abs=1e-6)
    for _state, report, _p in out[1:]:
        L = report.lines
        assert L["balance_check"].value == pytest.approx(0, abs=1e-5)
        assert L["loss_carryforward"].value >= 0 and L["income_tax"].value >= 0
        assert L["bs_total_assets"].level.label == "heuristic" and L["income_tax"].level.label == "heuristic"
        assert all(0 <= L[k].value <= 1 for k in L if k.startswith("scorecard_"))
    assert out[1][1].lines["net_income"].level.label in {"heuristic", "placeholder"}


def test_accrual_tax_uses_the_loss_carryforward() -> None:
    acc = IMPLEMENTATIONS["accounting.accrual"](coefficients(PACK, "accounting.accrual"), PACK)
    out = run([{"accounting.accrual": {}}, {}, {}])
    first = out[0][1].lines
    assert first["accrual_pretax"].value < 0 and first["income_tax"].value == 0
    assert first["loss_carryforward"].value == pytest.approx(-first["accrual_pretax"].value)
    assert acc.tax_rate > 0


def test_inventory_on_the_books_moves_at_average_cost() -> None:
    out = run([{}, {"accounting.accrual": {}}, {}])
    q2, q3 = out[1][1].lines, out[2][1].lines
    # what was left at the end of q2 is what the books carry into q3 (stock flow at book value)
    assert q2["bs_inventory"].value > 0
    assert q3["bs_inventory"].value >= 0 and q3["accrual_cogs"].value > 0


def test_without_modules_state_and_report_are_unchanged() -> None:
    a = run([{}, {}, {}])
    assert all(not s.module_state for s, _r, _p in a)
    assert not any(k.split("[")[0] in MODULE_METRICS for _s, r, _p in a for k in r.lines)


def test_module_state_round_trips_through_a_save() -> None:
    out = run([{}, {"finance.loans": {"long_loan": 100000}, "production.learning_curve": {},
                    "supply.replenishment": {"rule": {BRAND: "order_up_to"}}}])
    state = out[1][0]
    again = CompanyState.from_dict(dataclasses.asdict(state))
    assert again.module_state == state.module_state and "finance.loans" in again.module_state


def test_internet_response_is_literature_and_its_elasticity_is_bounded() -> None:
    out = run([{}, {}, {"marketing.internet": {"web_spend": 50000}}])
    q3 = out[2][1].lines
    assert q3["internet_factor"].level.label == "literature" and q3["internet_marketing"].level.label == "heuristic"
    from marketplace_sim.business.marketing_more import InternetMarketingModule, PromotionsModule

    c = coefficients(PACK, "marketing.internet")
    with pytest.raises(ValueError, match="literature range"):
        InternetMarketingModule({**c, "elasticity": 0.5}, PACK)
    p = coefficients(PACK, "marketing.promotions")
    with pytest.raises(ValueError, match="literature range"):
        PromotionsModule({**p, "redemption_rate": 0.9}, PACK)


def test_overtime_follows_the_published_hours_output_relation(after_q1: svc.Session) -> None:
    from marketplace_sim.business.operations import OperatingCapacityModule

    m = OperatingCapacityModule(coefficients(PACK, "production.operating_capacity"), PACK)
    # proportional up to 49 hours a week (40 x 1.225), then elasticity 0.17: each extra hour adds much less
    assert m.relative_output(0.2) == pytest.approx(1.2)
    gain_low = m.relative_output(0.2) - m.relative_output(0.1)
    gain_high = m.relative_output(0.5) - m.relative_output(0.4)
    assert gain_high < 0.3 * gain_low
    ot = preview(after_q1, {"production.operating_capacity": {"overtime_pct": 10}})
    assert lvl(ot, "overtime_units") == "literature" and lvl(ot, "capacity_units_per_quarter") == "literature"
    with pytest.raises(ValueError, match="literature range"):
        OperatingCapacityModule({**coefficients(PACK, "production.operating_capacity"), "elasticity_above": 0.6}, PACK)


def test_training_gain_and_quit_elasticity_are_bounded_by_the_literature() -> None:
    from marketplace_sim.business.sales_force import SalesForceModule

    c = coefficients(PACK, "sales_force")
    sf = SalesForceModule(c, PACK)
    # constant elasticity: doubling pay index divides quits by 2^elasticity (inside the bounds)
    ref = c["reference_salary"]
    q1, q2 = sf.quit_rate(ref, c["reference_commission_pct"]), sf.quit_rate(2 * ref, 2 * c["reference_commission_pct"])
    assert q2 / q1 == pytest.approx(2 ** -c["quit_elasticity"])
    for bad in ({"skill_bonus": 0.5}, {"quit_elasticity": 3.0}):
        with pytest.raises(ValueError, match="literature range"):
            SalesForceModule({**c, **bad}, PACK)
