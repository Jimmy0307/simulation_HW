"""Sanity (not accuracy) tests for LiteratureDemand on synthetic data only."""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from marketplace_sim import modules as m
from marketplace_sim.control.html import render_results
from marketplace_sim.control.runner import run_scenario
from marketplace_sim.control.spec import load_spec
from marketplace_sim.demand import (
    LiteratureDemand,
    coefficients_for,
    default_coefficients,
    demand_for,
    need_similarity,
)
from marketplace_sim.engine import CompanyState, Plan, advance
from marketplace_sim.pack import ParamPack, load_pack, pack_from_dict
from marketplace_sim.provenance import Level, Tagged

ROOT = Path(__file__).parents[1]
SYNTHETIC = ROOT / "examples" / "synthetic"


@pytest.fixture()
def pack() -> ParamPack:
    return load_pack(SYNTHETIC)


def _offer(pack: ParamPack, price: float, adv: float = 0.0, firm: str = "us", brand: str = "X", segment: str = "1",
           markets: frozenset[str] | None = None, **kw: object) -> m.Offer:
    markets = markets if markets is not None else frozenset(mk.key for mk in pack.markets)
    return m.Offer(firm, brand, segment, price, 1.0, adv, markets, position=segment, **kw)  # type: ignore[arg-type]


def _units(model: LiteratureDemand, pack: ParamPack, offers: list[m.Offer], key: tuple[str, str] = ("us", "X")) -> float:
    return model.units(pack, offers).get(key, Tagged(0.0, Level.LITERATURE, "")).value


def _wtp(pack: ParamPack, segment: str = "1") -> float:
    return sum(mk.segments[segment].wtp for mk in pack.markets) / len(pack.markets)


def test_defaults_are_the_documented_literature_values() -> None:
    c = default_coefficients()
    assert (c["price_sensitivity"], c["ad_elasticity"], c["carryover"], c["distribution_elasticity"]) == (2.6, 0.24, 0.5, 1.0)


def test_price_up_demand_down(pack: ParamPack) -> None:
    model = LiteratureDemand(pack=pack)
    rival = _offer(pack, _wtp(pack), 10000, firm="r", brand="R")
    units = [_units(model, pack, [_offer(pack, f * _wtp(pack)), rival]) for f in (0.5, 0.8, 1.0, 1.2, 1.5, 3.0)]
    assert all(a > b for a, b in itertools.pairwise(units))


def test_price_elasticity_matches_the_logit_formula() -> None:
    raw = json.loads((SYNTHETIC / "pack.json").read_text(encoding="utf-8"))
    raw["segments"] = [s for s in raw["segments"] if s["id"] == "1"]  # one segment, one city: a single logit cell
    raw["markets"] = [{**raw["markets"][0], "segments": {"1": raw["markets"][0]["segments"]["1"]}}]
    pack = pack_from_dict(raw)
    model = LiteratureDemand(pack=pack)
    wtp = pack.markets[0].segments["1"].wtp
    q0 = model.detail(pack, [_offer(pack, wtp)])
    q1 = model.detail(pack, [_offer(pack, wtp * 1.001)])
    share = q0.units[("us", "X")] / q0.potential
    elasticity = math.log(q1.units[("us", "X")] / q0.units[("us", "X")]) / math.log(1.001)
    assert elasticity == pytest.approx(-2.6 * (1 - share), rel=0.01)


def test_advertising_has_diminishing_returns(pack: ParamPack) -> None:
    for shape in ("power", "adbudg"):
        model = LiteratureDemand({"ad_shape": shape}, pack=pack)
        spends = [0, 50_000, 100_000, 150_000, 200_000, 250_000]
        units = [_units(model, pack, [_offer(pack, _wtp(pack), a)]) for a in spends]
        gains = [b - a for a, b in itertools.pairwise(units)]
        assert all(g > 0 for g in gains)
        if shape == "power":
            assert all(a > b for a, b in itertools.pairwise(gains))
    capped = LiteratureDemand({"ad_shape": "adbudg"}, pack=pack)
    huge = _units(capped, pack, [_offer(pack, _wtp(pack), 1e15)])
    none = _units(capped, pack, [_offer(pack, _wtp(pack), 0)])
    assert huge / none <= 1.5 + 1e-9  # ADBUDG ceiling


def test_shares_sum_to_one_with_outside_option(pack: ParamPack) -> None:
    model = LiteratureDemand(pack=pack)
    offers = [_offer(pack, _wtp(pack, s) * f, a, firm=fm, brand=f"{fm}{s}", segment=s)
              for fm, f, a in (("us", 1.0, 30_000), ("r1", 0.9, 10_000), ("r2", 1.1, 60_000)) for s in ("1", "2", "3")]
    detail = model.detail(pack, offers)
    assert 0 < detail.inside_units < detail.potential
    assert sum(detail.units.values()) == pytest.approx(detail.inside_units)
    firms: dict[str, float] = {}
    for (firm, _), units in detail.units.items():
        firms[firm] = firms.get(firm, 0.0) + units
    assert sum(u / detail.inside_units for u in firms.values()) == pytest.approx(1.0)


def test_engine_market_share_sums_to_one_across_firms(pack: ParamPack) -> None:
    state = CompanyState.initial(pack)
    state.fixed_capacity_units, state.stores_open = 50, [s.key for s in pack.stores]
    plan = Plan.from_dict({"brands": [{"name": "X", "brand_type": "A", "price": 700, "production": 10_000,
                                       "advertising": 20_000}]})
    _, report = advance(state, plan, pack, competitors=[m.BaselineBot("r")])
    ours = report.lines["market_share"].value
    rival_units = report.lines["market_units_total"].value - report.lines["units_sold[X]"].value
    assert 0 < ours < 1
    assert ours + rival_units / report.lines["market_units_total"].value == pytest.approx(1.0)


@pytest.mark.parametrize("price, adv", [(1e-9, 0.0), (1e12, 0.0), (700, 1e18), (700, -5e5), (float("1e300"), 1e300)])
def test_extreme_inputs_stay_finite_and_bounded(pack: ParamPack, price: float, adv: float) -> None:
    model = LiteratureDemand(pack=pack)
    detail = model.detail(pack, [_offer(pack, price, adv), _offer(pack, 700, 10_000, firm="r", brand="R")])
    assert all(math.isfinite(v) and v >= 0 for v in detail.units.values())
    assert detail.inside_units <= detail.potential + 1e-6


def test_no_price_or_no_outlet_means_no_demand(pack: ParamPack) -> None:
    model = LiteratureDemand(pack=pack)
    assert _units(model, pack, [_offer(pack, 0.0)]) == 0
    assert _units(model, pack, [_offer(pack, 700, markets=frozenset())]) == 0


def test_distribution_store_beats_web_beats_nothing(pack: ParamPack) -> None:
    model = LiteratureDemand(pack=pack)
    market = pack.markets[0].key
    store = _units(model, pack, [_offer(pack, 700, coverage=((market, 1.0),))])
    web = _units(model, pack, [_offer(pack, 700, coverage=((market, 0.5),))])
    assert store > web > 0
    cov = m.coverage(pack, {market}, set(), 0.5)
    assert cov == {market: 1.0}
    cov = m.coverage(pack, set(), {pack.web_centers[0].key}, 0.5)
    assert set(cov.values()) == {0.5}


def test_need_similarity_drives_cross_segment_appeal(pack: ParamPack) -> None:
    seg = {s.id: s for s in pack.segments}
    for a in seg.values():
        assert need_similarity(a, a) == 1.0
        for b in seg.values():
            assert 0.0 <= need_similarity(a, b) <= 1.0
            assert need_similarity(a, b) == pytest.approx(need_similarity(b, a))
    # A brand designed for segment "1" sells more into the segment whose needs are closer to "1".
    raw = json.loads((SYNTHETIC / "pack.json").read_text(encoding="utf-8"))

    def units_in(target: str) -> float:
        only = {**raw, "markets": [{**mk, "segments": {target: mk["segments"][target]}} for mk in raw["markets"]]}
        p = pack_from_dict(only)
        return LiteratureDemand(pack=p).detail(p, [_offer(p, _wtp(p, target), segment="1")]).units.get(("us", "X"), 0.0)

    others = sorted(("2", "3"), key=lambda b: need_similarity(seg["1"], seg[b]))
    low, high = (units_in(b) for b in others)
    assert units_in("1") > high >= low


def test_goodwill_carries_over_between_quarters(pack: ParamPack) -> None:
    state = CompanyState.initial(pack)
    state.fixed_capacity_units, state.stores_open = 50, [pack.stores[0].key]
    spend = Plan.from_dict({"brands": [{"name": "X", "brand_type": "A", "price": 700, "production": 5000,
                                        "advertising": 80_000}]})
    silent = Plan.from_dict({"brands": [{"name": "X", "brand_type": "A", "price": 700, "production": 5000}]})
    after_spend, _ = advance(state, spend, pack, competitors=[])
    assert after_spend.ad_stock["X"] == 80_000
    after_silence, with_memory = advance(after_spend, silent, pack, competitors=[])
    assert after_silence.ad_stock["X"] == pytest.approx(40_000)
    fresh = CompanyState.from_dict({**after_spend.to_dict(), "ad_stock": {}})
    _, no_memory = advance(fresh, silent, pack, competitors=[])
    assert with_memory.lines["units_demanded[X]"].value > no_memory.lines["units_demanded[X]"].value
    assert CompanyState.from_dict(after_silence.to_dict()).ad_stock == after_silence.ad_stock


def test_coefficients_overridable_and_validated(pack: ParamPack) -> None:
    raw = json.loads((SYNTHETIC / "pack.json").read_text(encoding="utf-8"))
    raw["demand"]["coefficients"]["price_sensitivity"] = 4.0
    assert coefficients_for(pack_from_dict(raw))["price_sensitivity"] == 4.0
    raw["demand"]["coefficients"]["bogus"] = 1
    with pytest.raises(ValueError):
        coefficients_for(pack_from_dict(raw))
    with pytest.raises(ValueError):
        LiteratureDemand({"ad_shape": "wiggly"}, pack=pack)


def test_model_switch_and_downstream_levels(pack: ParamPack, tmp_path: Path) -> None:
    raw = json.loads((SYNTHETIC / "pack.json").read_text(encoding="utf-8"))
    assert isinstance(demand_for(pack), LiteratureDemand)
    raw["demand"]["model"] = "placeholder"
    assert isinstance(demand_for(pack_from_dict(raw)), m.PlaceholderDemand)
    state = CompanyState.initial(pack)
    state.fixed_capacity_units, state.stores_open = 50, [pack.stores[0].key]
    plan = Plan.from_dict({"brands": [{"name": "X", "brand_type": "A", "price": 700, "production": 500}]})
    _, report = advance(state, plan, pack)
    lines = report.lines
    assert lines["units_demanded[X]"].level is Level.LITERATURE
    assert lines["revenue"].level is Level.LITERATURE and lines["market_share"].level is Level.LITERATURE
    assert lines["net_income"].level is Level.PLACEHOLDER and lines["cash_end"].level is Level.PLACEHOLDER
    assert lines["capex_capacity"].level is Level.VERIFIED  # cost side untouched
    # Upgrade path: a validated fitted file turns the same form into ESTIMATED; a failing one is refused.
    fitted = tmp_path / "fitted.json"
    good = {"schema": "marketplace-sim/fitted-demand@1", "coefficients": {"price_sensitivity": 3.1},
            "validation": {"holdout_quarter": 3, "mape": 0.12, "direction_hit_rate": 0.8}}
    fitted.write_text(json.dumps(good), encoding="utf-8")
    _, est = advance(state, plan, pack, demand=m.FittedDemand(str(fitted), pack=pack))
    assert est.lines["units_demanded[X]"].level is Level.ESTIMATED and est.lines["revenue"].level is Level.ESTIMATED
    fitted.write_text(json.dumps({**good, "validation": {"mape": 0.45, "direction_hit_rate": 0.8}}), encoding="utf-8")
    with pytest.raises(ValueError):
        advance(state, plan, pack, demand=m.FittedDemand(str(fitted), pack=pack))


def test_deterministic(pack: ParamPack) -> None:
    model = LiteratureDemand(pack=pack)
    offers = [_offer(pack, 690, 1234), replace(_offer(pack, 710, 999, firm="r", brand="R"), quality=0.7)]
    assert model.units(pack, offers) == model.units(pack, offers)


def test_control_plane_shows_literature_level(tmp_path: Path) -> None:
    result = run_scenario(load_spec(ROOT / "examples" / "scenarios" / "price-war.yaml")).to_dict()
    weakest = result["summary"]["weakest_level"]
    assert weakest["revenue"] == "literature" and weakest["market_share"] == "literature"
    assert weakest["capex_capacity"] == "verified" and weakest["cash_end"] == "placeholder"
    page = render_results([result], "x")
    assert 'class="lv-l"' in page and "literature" in page
