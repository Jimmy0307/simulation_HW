"""Q1-to-Q2 evidence reconciliation and sales-led capacity planning.

Marketplace PHP calculations remain opaque. User-owned local HAR is read in
memory; only whitelisted business figures are emitted. No live game writes.
"""
from __future__ import annotations

from math import ceil, isfinite
from typing import Any, Mapping

RECEIPTS = frozenset({"sales", "interest_income", "lic_income", "other_income", "inc_comm", "inc_short_l", "inc_emer_l", "rep_cd"})
PAYMENTS = frozenset({"rebates", "production", "rd", "advertising", "inet_exp", "sf", "so", "wsc_exp", "mr", "shipping", "excess_capacity", "income_taxes", "interest", "lic_fee", "other_exp", "fixed_cap", "rep_bank_l", "rep_emer_l", "inc_cd"})


def _number(value: Any) -> float:
    number = float(value)
    if not isfinite(number):
        raise ValueError("Non-finite numeric value")
    return number


def _section_item(view: Mapping[str, Any], item_id: str) -> float:
    for section in view.get("staticData", {}).get("sections", []):
        for item in section.get("items", []):
            if item.get("id") == item_id:
                return _number(item["quarters"][0])
    raise ValueError(f"Missing historical item: {item_id}")


def _items(view: Mapping[str, Any], container: str) -> dict[str, float]:
    return {str(item["id"]): _number(item["value"]) for item in view.get(container, {}).get("items", [])}


def _calculated_item(view: Mapping[str, Any], item_id: str) -> float:
    for item in view.get("calculate", {}).get("items", []):
        if item.get("id") == item_id:
            return _number(item["quarters"][0])
    raise ValueError(f"Missing pro forma item: {item_id}")


def read_har_views(har: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Read observed view responses only; discard transport/auth data."""
    import json
    from urllib.parse import urlsplit

    allowed = {
        "CashFlow", "BalanceSheet", "IncomeStatement", "ProFormaCashFlow",
        "ExtFactorySimulation", "Stock", "CD", "OperatingCapacity",
        "CostOfProduction", "ModifyBrand", "DemandProjection",
    }
    views: dict[str, dict[str, Any]] = {}
    for entry in har.get("log", {}).get("entries", []):
        request = entry.get("request", {})
        parsed = urlsplit(request.get("url", ""))
        if not parsed.path.endswith("/backend-json.php"):
            continue
        service = parsed.query.split("&", 1)[0]
        if service not in allowed:
            continue
        try:
            query = json.loads(request.get("postData", {}).get("text", "{}"))
            response = json.loads(entry.get("response", {}).get("content", {}).get("text", ""))
        except (ValueError, TypeError, KeyError):
            continue
        if (
            query.get("method") == "view"
            and response.get("error") == 0
            and isinstance(response.get("result"), dict)
        ):
            views[service] = response["result"]
    return views


def reconcile_quarters(views: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Reconcile Q1 final bank cash to two different Q2 snapshot outputs."""
    missing = {"CashFlow", "BalanceSheet", "ProFormaCashFlow", "ExtFactorySimulation"} - views.keys()
    if missing:
        return {"status": "MISSING_OBSERVED_SCREENS", "screens": sorted(missing)}
    q1_bank = _section_item(views["CashFlow"], "cash")
    q1_cd = _section_item(views["BalanceSheet"], "cd")
    q2 = views["ProFormaCashFlow"]
    inputs = _items(q2, "dynamicData")
    known = RECEIPTS | PAYMENTS
    unknown = sorted(k for k, value in inputs.items() if k not in known and value != 0)
    net = sum(inputs.get(k, 0) for k in RECEIPTS) - sum(inputs.get(k, 0) for k in PAYMENTS)
    bridged = round(q1_bank + net, 2)
    accounting = views["ExtFactorySimulation"].get("calculate", {}).get("accounting", {})
    if "cash" not in accounting:
        return {"status": "MISSING_SIMULATION_CASH"}
    simulated = _number(accounting["cash"])
    proforma = _calculated_item(q2, "cash")
    net_income = accounting.get("netIncome")
    operating_receipts = RECEIPTS - {"inc_comm", "inc_short_l", "inc_emer_l", "rep_cd"}
    operating_payments = PAYMENTS - {"fixed_cap", "rep_bank_l", "rep_emer_l", "inc_cd"}
    visible_operating_cash = (
        sum(inputs.get(k, 0) for k in operating_receipts)
        - sum(inputs.get(k, 0) for k in operating_payments)
    )
    return {
        "status": "RECONCILED" if not unknown and abs(bridged - simulated) < 0.01 else "NEEDS_REVIEW",
        "source": "USER_CAPTURED_HAR_Q1_ACTUAL_PLUS_Q2_CURRENT_VIEW",
        "q1_bank_cash": q1_bank,
        "q1_cd_separate_from_bank_cash": q1_cd,
        "q2_equity_input_not_confirmed_issued": inputs.get("inc_comm", 0),
        "q2_recurring_channel_expense": inputs.get("so", 0),
        "q2_interest_income": inputs.get("interest_income", 0),
        "q2_current_view_net_flows": round(net, 2),
        "q2_cash_bridge": bridged,
        "q2_factory_simulated_cash_at_current_inputs": simulated,
        "q2_proforma_calculated_cash": proforma,
        "factory_minus_proforma": round(simulated - proforma, 2),
        "q2_factory_simulated_net_income": _number(net_income) if net_income is not None else None,
        "q2_visible_operating_cash_before_financing": round(visible_operating_cash, 2),
        "q2_net_income_minus_visible_operating_cash_unexplained": (
            round(_number(net_income) - visible_operating_cash, 2)
            if net_income is not None else None
        ),
        "unknown_nonzero_finance_fields": unknown,
        "caution": "Not finalized Q2 cash. CD is not bank cash until withdrawn. Pro Forma may be stale.",
    }


def brand_cost_quotes(views: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Expose observed COGS quote points, not a reconstructed formula."""
    brands = views.get("CostOfProduction", {}).get("dynamicData", {}).get("brands", [])
    return [
        {
            "brand": b.get("brandName", "unnamed"),
            "type": b.get("brandType", ""),
            "quotes": [
                {"units": int(q["units"]), "unit_cost": round(_number(q["cost"]), 2)}
                for q in b.get("cogsEstimates", [])
            ],
        }
        for b in brands
    ]


def plan_sales_to_capacity(
    brand_demand: Mapping[str, int] | None,
    *,
    days: int = 65,
    productivity_pct: float = 70.0,
    maximum_daily_capacity: int = 16,
) -> dict[str, Any]:
    """Planning envelope only, NOT the Marketplace factory formula."""
    if brand_demand is None:
        return {"status": "WAITING_FOR_SALES_FORECAST", "requires": "brand_demand units by brand name"}
    if (
        type(days) is not int or days <= 0 or not 0 < productivity_pct <= 100
        or type(maximum_daily_capacity) is not int or maximum_daily_capacity <= 0
    ):
        raise ValueError("Invalid days/productivity/maximum daily capacity")
    if not brand_demand or any(type(n) is not int or n < 0 for n in brand_demand.values()):
        raise ValueError("Demand must be a nonempty mapping of brand to nonnegative integer units")
    total = sum(brand_demand.values())
    result: dict[str, Any] = {
        "status": "PLANNING_ENVELOPE_ONLY",
        "sales_forecast": dict(brand_demand),
        "quarter_workdays_assumption": days,
        "observed_productivity_input_pct": productivity_pct,
        "observed_fixed_daily_capacity": maximum_daily_capacity,
        "scenarios": {},
        "caution": "Productivity is applied as a heuristic. No changeover, overtime, worker, or cash simulation. Validate in game.",
    }
    for label, ratio in (
        ("most_likely", 1.0), ("pessimistic_50pct", 0.5), ("worst_case_25pct", 0.25)
    ):
        units = ceil(total * ratio)
        adjusted = ceil(units / (days * productivity_pct / 100))
        result["scenarios"][label] = {
            "demand_units": units,
            "daily_capacity_unadjusted": ceil(units / days),
            "daily_capacity_with_productivity_heuristic": adjusted,
            "within_fixed_daily_limit_heuristic": adjusted <= maximum_daily_capacity,
        }
    return result


def evaluate_cash_gates(scenario_cash: Mapping[str, float] | None) -> dict[str, Any]:
    """Teacher guardrails based on actual rerun factory/pro forma observations."""
    if scenario_cash is None:
        return {
            "status": "WAITING_FOR_FACTORY_SIMULATION_AND_PRO_FORMA_LOAD_DATA",
            "most_likely_target": 500000,
            "pessimistic_50pct_target": 300000,
        }
    required = {"most_likely": 500000.0, "pessimistic_50pct": 300000.0}
    if not set(required).issubset(scenario_cash) or "worst_case_25pct" not in scenario_cash:
        raise ValueError("All three observed scenario cash results are required")
    return {
        "status": "OBSERVED_PRO_FORMA_GATE_RESULTS",
        "gates": {
            k: {"ending_cash": _number(scenario_cash[k]), "required": target,
                "pass": _number(scenario_cash[k]) >= target}
            for k, target in required.items()
        },
        "worst_case": {
            "ending_cash": _number(scenario_cash["worst_case_25pct"]),
            "nonnegative": _number(scenario_cash["worst_case_25pct"]) >= 0,
        },
    }
