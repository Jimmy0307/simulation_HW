"""Q2 cross-functional decision gates for Marketplace planning.

Pure calculations only. No game access, no private scenarios or account data.
All cash outputs must be marked as model-only until official Pro Forma confirms.
"""
from __future__ import annotations

from math import isfinite
from typing import Mapping


def _nonnegative(name: str, value: float) -> float:
    n = float(value)
    if not isfinite(n) or n < 0:
        raise ValueError(f"{name}: expected finite nonnegative input")
    return n


def sales_equivalent_forecast(
    full_sellers: int,
    support_staff: int,
    *,
    per_seller_units: float,
    support_selling_fraction: float,
) -> dict[str, float]:
    """Sensitivity case, not the game's undisclosed demand function."""
    if not isinstance(full_sellers, int) or not isinstance(support_staff, int):
        raise ValueError("Staff counts must be integers")
    full = _nonnegative("full_sellers", full_sellers)
    support = _nonnegative("support_staff", support_staff)
    each = _nonnegative("per_seller_units", per_seller_units)
    fraction = _nonnegative("support_selling_fraction", support_selling_fraction)
    if fraction > 1:
        raise ValueError("Support selling fraction cannot exceed one")
    return {
        "full_seller_forecast": full * each,
        "support_equivalent_forecast": support * fraction * each,
        "total_units_sensitivity": (full + support * fraction) * each,
        "evidence_status": "ASSUMPTION_BASED_SENSITIVITY",
    }


def ad_budget(
    *,
    brand_ads: int,
    cost_per_ad: float,
    media_insertions: Mapping[str, int],
    media_price_per_insert: Mapping[str, float],
    combined_cap: float,
) -> dict[str, float | bool]:
    """Conservatively assume an advertising limit covers design + media."""
    if not isinstance(brand_ads, int) or brand_ads < 0:
        raise ValueError("brand_ads must be nonnegative integer")
    design = brand_ads * _nonnegative("cost_per_ad", cost_per_ad)
    media = 0.0
    for channel, count in media_insertions.items():
        if not isinstance(count, int) or count < 0 or channel not in media_price_per_insert:
            raise ValueError(f"Invalid media insertion: {channel}")
        media += count * _nonnegative(channel, media_price_per_insert[channel])
    limit = _nonnegative("combined_cap", combined_cap)
    total = design + media
    return {
        "ad_design": design,
        "media_placement": media,
        "combined_spend": total,
        "headroom": limit - total,
        "within_combined_cap": total <= limit,
    }


def price_change_break_even_uplift(
    old_price: float,
    candidate_price: float,
    marginal_unit_cost: float,
) -> float:
    """Required relative unit-demand gain for equal gross contribution."""
    old = _nonnegative("old_price", old_price)
    new = _nonnegative("candidate_price", candidate_price)
    cost = _nonnegative("marginal_unit_cost", marginal_unit_cost)
    if old <= cost or new <= cost:
        raise ValueError("Both prices must exceed modeled marginal unit cost")
    return (old - cost) / (new - cost) - 1.0


def incremental_units_to_cover_spend(extra_spend: float, margin_per_unit: float) -> float:
    amount = _nonnegative("extra_spend", extra_spend)
    margin = _nonnegative("margin_per_unit", margin_per_unit)
    if margin <= 0:
        raise ValueError("Contribution per unit must be positive")
    return amount / margin


def proforma_cash_gates(
    scenario_cash: Mapping[str, float] | None,
    *,
    normal_minimum: float,
    half_demand_minimum: float,
) -> dict:
    """Never label incomplete or synthetic cash as official."""
    if scenario_cash is None:
        return {"status": "WAITING_FOR_OFFICIAL_PRO_FORMA"}
    expected = ("normal", "half_demand", "quarter_demand")
    if any(key not in scenario_cash for key in expected):
        return {"status": "MISSING_SCENARIO", "required": list(expected)}
    cash = {key: float(scenario_cash[key]) for key in expected}
    if any(not isfinite(v) for v in cash.values()):
        raise ValueError("Cash values must be finite")
    gates = {
        "normal": cash["normal"] >= _nonnegative("normal_minimum", normal_minimum),
        "half_demand": cash["half_demand"] >= _nonnegative("half_demand_minimum", half_demand_minimum),
        "quarter_demand_survival": cash["quarter_demand"] >= 0,
    }
    return {"status": "USER_SUPPLIED_CASH_GATE_RESULT", "cash": cash, "gates": gates,
            "all_pass": all(gates.values()), "source_not_verified": True}
