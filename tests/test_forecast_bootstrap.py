"""Q2 bootstrap tests use synthetic brands, prices, and estimates only."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from marketplace_sim.forecast_bootstrap import bootstrap_plan, quote_cost

COSTS = {
    "synthetic_mountain": [[100, 900], [250, 650], [500, 550]],
    "synthetic_speed": [[100, 990], [250, 720], [500, 590]],
}
PLAN = {
    "name": "synthetic_test",
    "store_staff": 4,
    "web_staff": 1,
    "brands": [
        {"name": "synthetic_mountain", "type": "M", "price": 1300},
        {"name": "synthetic_speed", "type": "S", "price": 1500},
    ],
}


def run(seed: int = 123, web_mode: str = "store_only") -> dict:
    return bootstrap_plan(
        PLAN, COSTS, mountain_weight=0.5, starting_bank=300000,
        financing=500000, interest=4500, fixed_cash=150000,
        draws=2000, seed=seed, web_mode=web_mode,
    )


def test_cost_quote_points_are_preserved() -> None:
    assert np.allclose(
        quote_cost(np.array([100, 250, 500]), COSTS["synthetic_mountain"]),
        [900, 650, 550],
    )
    assert quote_cost(np.array([50]), COSTS["synthetic_mountain"])[0] > 900


def test_reproducible_and_demand_bounds() -> None:
    first, second = run(), run()
    assert first["units"] == second["units"]
    assert first["units"]["p05"] < first["units"]["p50"] < first["units"]["p95"]
    assert first["forecast_status"].endswith("NOT_EMPIRICAL_CI")


def test_financing_not_assumed_settled() -> None:
    result = run()
    assert result["cash_without_draft_equity"]["p50"] == round(
        result["cash_with_draft_equity"]["p50"] - 500000, 2
    )
    assert result["stress"]["50pct"]["units"]["p50"] < result["units"]["p50"]


def test_web_sales_are_optional() -> None:
    base = run(seed=2)
    upside = run(seed=2, web_mode="speculative_web")
    assert base["units_speculative_web"]["p50"] == 0
    assert upside["units"]["p50"] >= base["units"]["p50"]


def test_bad_cost_curve_rejected() -> None:
    with pytest.raises(ValueError):
        quote_cost(np.array([100]), [[100, 200], [250, 250]])
