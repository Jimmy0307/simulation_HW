from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace_sim import modules as m
from marketplace_sim.cli import main as mpsim
from marketplace_sim.engine import CompanyState, Plan, advance
from marketplace_sim.metrics import METRICS, lookup
from marketplace_sim.pack import load_pack
from marketplace_sim.provenance import Level, Tagged, total

ROOT = Path(__file__).parents[1]
SYNTHETIC = ROOT / "examples" / "synthetic"


@pytest.fixture()
def pack():  # type: ignore[no-untyped-def]
    return load_pack(SYNTHETIC)


def test_levels_combine_to_weakest() -> None:
    a = Tagged(2, Level.VERIFIED, "a")
    b = Tagged(3, Level.PLACEHOLDER, "b")
    assert (a + b).level is Level.PLACEHOLDER and (a + b).value == 5
    assert total([a, a], "t").level is Level.VERIFIED
    assert total([], "t", empty_level=Level.DERIVED).level is Level.DERIVED


def test_verified_modules_follow_the_measured_rules(pack) -> None:  # type: ignore[no-untyped-def]
    # EXP-02 rule: capacity investment is the chosen option's cost; units/quarter = units/day x days.
    option = pack.capacity_options[2]
    capex = m.capacity_purchase(pack, option.units)
    assert capex.value == option.cost and capex.level is Level.VERIFIED
    assert m.quarterly_capacity(pack, 10).value == 10 * pack.days_per_quarter
    # EXP-01 rule: interest = cd x annual rate / 4 / 100.
    cd, interest = m.cd_quarter(pack, 0, 1000, 0)
    assert cd.value == 1000 and interest.value == pytest.approx(1000 * pack.finance["cd_rate_annual_percent"] / 400)
    # EXP-11/12 rule: opening adds setup cost only; already-open outlets cost nothing to "open" again.
    keys = [s.key for s in pack.stores[:2]]
    setup = m.opening_cost(pack.stores, keys, set(), "stores")
    assert setup.value == sum(s.setup_cost for s in pack.stores[:2]) and setup.level is Level.VERIFIED
    assert m.opening_cost(pack.stores, keys, set(keys), "stores").value == 0
    with pytest.raises(ValueError):
        m.capacity_purchase(pack, 12345)


def test_advance_reconciles_cash_and_tags_every_line(pack) -> None:  # type: ignore[no-untyped-def]
    state = CompanyState.initial(pack)
    plan = Plan.from_dict({"capacity_increase": pack.capacity_options[1].units, "open_stores": [pack.stores[0].key],
                           "cd": {"deposit": 500}, "stock_issue": [{"shares": 10, "price": 7}]})
    new, report = advance(state, plan, pack)
    lines = report.lines
    expected = (state.cash + 70 - 500 + lines["cd_interest"].value - lines["store_setup"].value
                - lines["design_cost"].value - lines["outlet_lease"].value - lines["capex_capacity"].value)
    assert lines["cash_end"].value == pytest.approx(expected)
    assert all(isinstance(v.level, Level) for v in lines.values())
    assert lines["capex_capacity"].level is Level.VERIFIED and lines["stock_raised"].level is Level.DERIVED
    assert new.quarter == state.quarter + 1 and new.fixed_capacity_units == pack.capacity_options[1].units
    assert new.cash_level == lines["cash_end"].level.label


def test_sales_need_open_outlets_and_carry_the_demand_level(pack) -> None:  # type: ignore[no-untyped-def]
    state = CompanyState.initial(pack)
    state.fixed_capacity_units = 20
    state.stores_open = [pack.stores[0].key]
    plan = Plan.from_dict({"brands": [{"name": "X", "brand_type": "A", "price": 700, "production": 100}]})
    _, report = advance(state, plan, pack)  # default: literature demand
    assert report.lines["units_sold[X]"].level is Level.LITERATURE
    assert report.lines["revenue"].level is Level.LITERATURE
    assert report.lines["operating_profit_before_tax"].level is Level.PLACEHOLDER  # production cost is placeholder
    assert 0 < report.lines["units_sold[X]"].value <= 100
    _, placeholder = advance(state, plan, pack, demand=m.PlaceholderDemand())
    assert placeholder.lines["units_sold[X]"].level is Level.PLACEHOLDER
    _, closed = advance(CompanyState.initial(pack), plan, pack)
    assert "units_sold[X]" not in closed.lines


def test_fitted_and_replay_interfaces_fail_explicitly(pack) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(NotImplementedError):
        m.FittedDemand("missing").units(pack, [])
    with pytest.raises(KeyError):
        m.ReplayCompetitors({}).offers(pack, 1, __import__("random").Random(0))


def test_cli_new_play_compare_explain(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    save = tmp_path / "save.json"
    mpsim(["new", "--params", str(SYNTHETIC), "--out", str(save)])
    for quarter in ("q1", "q2", "q3"):
        mpsim(["play", str(save), "--decisions", str(ROOT / "examples" / "demo" / f"{quarter}.yaml")])
    data = json.loads(save.read_text())
    assert data["state"]["quarter"] == 4 and len(data["history"]) == 3
    capsys.readouterr()
    mpsim(["compare", str(save), str(ROOT / "examples" / "demo" / "plans" / "*.yaml")])
    table = capsys.readouterr().out
    assert "cautious" in table and "aggressive" in table and "[V]" in table and "[P]" in table
    mpsim(["explain", "cd_interest"])
    assert "verified" in capsys.readouterr().out
    assert lookup("units_sold[Anything]") is METRICS["units_sold[brand]"]
