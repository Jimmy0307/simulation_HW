"""Synthetic-only regression for total-production volume on game cost quotes."""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from marketplace_sim import forecast_bootstrap as fb


def test_cost_quote_volume_is_total_company_output(monkeypatch) -> None:
    quotes = {
        "Alpha": [[100, 950], [250, 720], [500, 600]],
        "Beta": [[100, 1000], [250, 770], [500, 650]],
    }
    plan = {
        "name": "synthetic_total_volume_regression",
        "store_staff": 4,
        "web_staff": 0,
        "brands": [
            {"name": "Alpha", "type": "M", "price": 1300},
            {"name": "Beta", "type": "S", "price": 1500},
        ],
    }
    original = fb.quote_cost
    volumes: list[np.ndarray] = []

    def recorded(units: np.ndarray, points: list[list[float]]) -> np.ndarray:
        volumes.append(np.asarray(units).copy())
        return original(units, points)

    monkeypatch.setattr(fb, "quote_cost", recorded)
    result = fb.bootstrap_plan(
        plan, quotes, mountain_weight=0.5, starting_bank=300000,
        financing=0, interest=0, fixed_cash=0, draws=2000, seed=42,
    )

    # Two brands × (initial calculation + three stress scenarios).
    assert len(volumes) == 8
    for i in range(0, len(volumes), 2):
        assert np.array_equal(volumes[i], volumes[i + 1])
    # "normal" stress is the same total production as the initial quote.
    assert np.array_equal(volumes[0], volumes[2])
    assert result["cost_quote_volume_basis"] == "TOTAL_PRODUCTION_ACROSS_ALL_BRANDS"

    # With a company output >=100, brand-level sales below 100 must NOT
    # trigger quote extrapolation. Below-quote fraction is one only when
    # the company's total production is <100, not per individual brand.
    expected = float(np.mean(volumes[0] < 100))
    assert abs(result["pct_quantity_below_quote_min"] - expected) < 0.0001
