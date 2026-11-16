"""Offline conditional parametric-bootstrap Q2 forecasts.

No credentials, network calls, private game capture, or quarter submission.
The priors describe hypothetical sales, not empirically observed demand.
Install the optional numpy dependency before running this module.
"""
from __future__ import annotations

from typing import Any
import numpy as np


def quote_cost(units: np.ndarray, points: list[list[float]]) -> np.ndarray:
    """Log-volume interpolation of observed *estimated* unit-cost quotes.

    Volume below the first point is explicitly unverified extrapolation.
    """
    x = np.asarray([p[0] for p in points], dtype=float)
    y = np.asarray([p[1] for p in points], dtype=float)
    if len(x) < 2 or np.any(np.diff(x) <= 0) or np.any(np.diff(y) > 1e-6):
        raise ValueError("Expected increasing volumes and nonincreasing cost quotes")
    u = np.asarray(units, dtype=float)
    safe = np.maximum(u, 1.0)
    result = np.interp(np.log(safe), np.log(x), y)
    lower = safe < x[0]
    result = np.where(
        lower,
        y[0] + (y[0] - y[1]) * np.log(x[0] / safe) / np.log(x[1] / x[0]),
        result,
    )
    result = np.where(safe > x[-1], y[-1], result)
    return np.where(u > 0, np.maximum(result, 0), 0)


def bootstrap_plan(
    plan: dict[str, Any],
    costs: dict[str, list[list[float]]],
    *,
    mountain_weight: float,
    starting_bank: float,
    financing: float,
    interest: float,
    fixed_cash: float,
    draws: int = 20000,
    seed: int = 20261116,
    web_mode: str = "store_only",
) -> dict[str, Any]:
    """Run scenario-based parametric bootstrap, NOT empirical sales bootstrap.

    Assumed storefront sales per person: 30+40*Beta(2,6), expected 40.
    Shared mean-one lognormal demand shock: log SD 0.20.
    Optional speculative web output per worker: 70% active, Uniform(0,30).
    Segment split: Beta(24*p, 24*(1-p)); within-segment beta(6,6).
    Quoted cost uncertainty is synthetic, with greater risk below 100 units.
    """
    if draws < 1000:
        raise ValueError("At least 1000 bootstrap replicates required")
    if not 0 < mountain_weight < 1:
        raise ValueError("Invalid mountain segment weight")
    if web_mode not in {"store_only", "speculative_web"}:
        raise ValueError("Unknown web model")
    rng = np.random.default_rng(seed)
    workers = int(plan["store_staff"])
    webstaff = int(plan["web_staff"])
    brands = list(plan["brands"])
    if workers < 1 or not brands or any(b["name"] not in costs for b in brands):
        raise ValueError("Missing planned brands or staffing")

    sales = rng.beta(2, 6, size=(draws, workers)) * 40 + 30
    shared = np.exp(rng.normal(-0.5 * 0.20**2, 0.20, size=draws))
    store_units = sales.sum(axis=1) * shared
    web_units = np.zeros(draws)
    if web_mode == "speculative_web" and webstaff:
        is_active = rng.random((draws, webstaff)) < 0.70
        web_units = (
            is_active * rng.uniform(0, 30, size=(draws, webstaff))
        ).sum(axis=1) * shared
    total = np.maximum(0, np.rint(store_units + web_units).astype(int))
    segment_share = rng.beta(
        24 * mountain_weight, 24 * (1 - mountain_weight), size=draws
    )
    mountain_units = rng.binomial(total, segment_share)
    speed_units = total - mountain_units
    by_brand: dict[str, np.ndarray] = {}
    for segment, count in (("M", mountain_units), ("S", speed_units)):
        candidates = [b for b in brands if b["type"] == segment]
        if len(candidates) == 1:
            by_brand[candidates[0]["name"]] = count
        elif len(candidates) == 2:
            split = rng.beta(6, 6, size=draws)
            first = rng.binomial(count, split)
            by_brand[candidates[0]["name"]] = first
            by_brand[candidates[1]["name"]] = count - first
        else:
            raise ValueError("Exactly one or two offered brands per segment expected")

    cost_total = np.zeros(draws)
    revenue = np.zeros(draws)
    outside_quotes = np.zeros(draws, dtype=int)
    brand_data: dict[str, dict[str, np.ndarray]] = {}

    for brand in brands:
        name = brand["name"]
        n = by_brand[name]
        quoted = quote_cost(n, costs[name])
        sigma = np.where(n < 100, 0.18, 0.08)
        multiplier = np.exp(rng.normal(size=draws) * sigma - sigma**2 / 2)
        unit_cost = np.where(n > 0, quoted * multiplier, 0)
        cost_total += n * unit_cost
        revenue += n * float(brand["price"])
        outside_quotes += np.where((n > 0) & (n < 100), n, 0)
        brand_data[name] = {
            "units": n,
            "unit_cost": unit_cost,
            "cost_multiplier": multiplier,
        }

    cash = starting_bank + financing + interest - fixed_cash + revenue - cost_total

    def summarize(a: np.ndarray) -> dict[str, float]:
        return {
            "mean": round(float(np.mean(a)), 2),
            "p05": round(float(np.quantile(a, 0.05)), 2),
            "p50": round(float(np.quantile(a, 0.50)), 2),
            "p95": round(float(np.quantile(a, 0.95)), 2),
        }

    by_brand_stats = {
        name: {
            "units": summarize(record["units"]),
            "unit_cost_if_sold": summarize(
                record["unit_cost"][record["units"] > 0]
            ),
        }
        for name, record in brand_data.items()
    }
    result: dict[str, Any] = {
        "plan": plan["name"],
        "web_model": web_mode,
        "draws": draws,
        "seed": seed,
        "forecast_status": "PARAMETRIC_ASSUMPTION_BOOTSTRAP_NOT_EMPIRICAL_CI",
        "units": summarize(total),
        "units_store_only": summarize(store_units),
        "units_speculative_web": summarize(web_units),
        "brands": by_brand_stats,
        "revenue": summarize(revenue),
        "production_cost": summarize(cost_total),
        "cash_with_draft_equity": summarize(cash),
        "cash_without_draft_equity": summarize(cash - financing),
        "sub_100_quote_units": summarize(outside_quotes),
        "pct_quantity_below_quote_min": round(
            float(np.mean(outside_quotes / np.maximum(total, 1))), 4
        ),
        "cash_gate_with_draft_equity": {
            "normal_above_500k": round(float(np.mean(cash >= 500000)), 4),
            "without_stock_above_500k": round(
                float(np.mean(cash - financing >= 500000)), 4
            ),
        },
        "stress": {},
    }
    for label, ratio, target in (
        ("normal", 1.0, 500000),
        ("50pct", 0.5, 300000),
        ("25pct", 0.25, 0),
    ):
        stress_revenue = np.zeros(draws)
        stress_cost = np.zeros(draws)
        for brand in brands:
            name = brand["name"]
            n = np.rint(by_brand[name] * ratio).astype(int)
            quoted = quote_cost(n, costs[name])
            stress_cost += n * quoted * brand_data[name]["cost_multiplier"]
            stress_revenue += n * float(brand["price"])
        stressed_cash = (
            starting_bank + financing + interest
            - fixed_cash + stress_revenue - stress_cost
        )
        result["stress"][label] = {
            "units": summarize(np.rint(total * ratio).astype(int)),
            "cash_at_quote_curve": summarize(stressed_cash),
            "prob_above_teacher_cash_target": round(
                float(np.mean(stressed_cash >= target)), 4
            ),
            "target": target,
            "cash_no_equity_median": summarize(
                stressed_cash - financing
            )["p50"],
            "p05_no_equity": summarize(stressed_cash - financing)["p05"],
        }
    result["limitations"] = [
        "No observed Q2 sales sample. Assumption-based, not empirical bootstrap.",
        "Price and advertising elasticities cannot yet be estimated.",
        "Per-brand volume below 100 extrapolates beyond server quote table.",
        "Financing is draft and cash is not official Pro Forma Cash Flow.",
        "Teacher cash-gate probabilities are model-conditional only.",
    ]
    return result
