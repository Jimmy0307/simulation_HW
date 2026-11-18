"""Factory decision surrogate regression tests (synthetic inputs only)."""
from __future__ import annotations

import pytest
from marketplace_sim.factory_policy import FactoryEvidence, Policy, simulate, quote_cost

E = FactoryEvidence(
    fixed_daily=16, workdays=65, productivity_pct=70,
    overtime_hours=(0.,1.,2.,3.,4.),
    overtime_productivity_pct=(70.,69.3,68.02,66.36,64.4),
    daily_capacity_chart_x=(1.,8.,14.,16.),
    labor_per_unit_chart_y=(500.,144.,120.,174.),
    overhead_per_unit_chart_y=(500.,80.,49.,44.),
    quotes_by_brand={"A":((100.,900.),(250.,700.),(500.,550.),(1000.,490.))},
)


def _run(c: int, h: int, n: int) -> dict[str, float]:
    return simulate(E,Policy(c,h),forecast_by_brand={"A":n},prices={"A":1300})


def test_capacity_and_overtime_graph_are_reproducible() -> None:
    assert E.capacity(16,0) == pytest.approx(728)
    assert E.capacity(16,4) == pytest.approx(1004.64)


def test_at_baseline_production_no_overtime_required() -> None:
    for c in (14,16):
        r=_run(c,4,560)
        assert r["stockout_units"] == 0
        assert r["overtime_hours_used"] == 0
        assert r["is_official_factory_result"] is False


def test_peak_needs_overtime() -> None:
    r = _run(14,4,840)
    assert r["stockout_units"] == 0
    assert 2 < r["overtime_hours_used"] < 4


def test_very_high_demand_exposes_capacity_constraint() -> None:
    assert _run(14,4,980)["stockout_units"] > 0
    assert _run(16,4,980)["stockout_units"] == 0


def test_quoted_cost_is_based_on_total_company_volume() -> None:
    extra=FactoryEvidence(**{**E.__dict__, "quotes_by_brand":{
        "A":E.quotes_by_brand["A"],
        "B":((100.,1000.),(250.,800.),(500.,650.),(1000.,570.))}})
    r=simulate(extra,Policy(14,4),
        forecast_by_brand={"A":250., "B":250.},
        prices={"A":1300., "B":1300.})
    assert r["direct_production_cost_est"] == pytest.approx(250*(550+650))
    assert quote_cost(500.,E.quotes_by_brand["A"]) == pytest.approx(550.)


def test_invalid_capacity_and_demand_are_rejected() -> None:
    with pytest.raises(ValueError):
        _run(18,4,400)
    with pytest.raises(ValueError):
        _run(14,0,-3)
