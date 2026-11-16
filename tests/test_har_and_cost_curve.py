"""Plain-HAR input, pack extras, the cost-of-production curve and statement actuals. Synthetic numbers only."""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import pytest

from marketplace_sim import modules as m
from marketplace_sim import reconcile as rc
from marketplace_sim.cost_curve import curve_cost, interpolate, validate
from marketplace_sim.engine import CompanyState, Plan, advance
from marketplace_sim.pack import load_pack, pack_from_dict
from marketplace_sim.pack_builder import _latest_views, build_pack_dict, merge_over_base
from marketplace_sim.provenance import Level
from marketplace_sysid.parameters import responses_from_har

ROOT = Path(__file__).resolve().parents[1]
SYNTH = json.loads((ROOT / "examples" / "synthetic" / "pack.json").read_text(encoding="utf-8"))
VOLUMES = (90.0, 270.0, 810.0, 2430.0)


def game_cost(units: float, material: float) -> float:
    """Invented smooth cost law used to make a synthetic estimate table (not the game's)."""
    return 37.0 + 6100.0 / units ** 0.71 + material * (1.0 - 0.013 * math.log(units))


def synthetic_pack_with_table() -> dict:
    data = json.loads(json.dumps(SYNTH))
    designs = [("A", ["c1", "c2"]), ("C", ["c1", "c4"])]
    table = []
    for code, comps in designs:
        material = sum(c["price"] for c in data["components"] if c["id"] in comps)
        table.append({"brand_type": code, "components": comps,
                      "points": [[u, game_cost(u, material)] for u in VOLUMES]})
    data["cost_estimates"] = table
    return data


def har_entry(service: str, quarter: int, current: int, result: dict) -> dict:
    body = {"method": "view", "parameters": [{"student": {"studentID": 1, "quarter": quarter}}]}
    payload = {"method": "view", "result": {"commonData": {"currentQuarter": current}, **result}}
    return {"request": {"url": f"https://game.example/mpl/backend-json.php?{service}", "headers": [{"name": "x-xsrf-token",
                                                                                                "value": "t"}],
                        "postData": {"text": json.dumps(body)}},
            "response": {"content": {"text": json.dumps(payload)}}}


def test_plain_har_keeps_bodies_and_quarter_only() -> None:
    statement = {"staticData": {"sections": [{"name": "", "sign": -1, "items": [{"id": "rd", "sign": 1, "quarters": ["77"]}]}]}}
    har = {"log": {"entries": [har_entry("IncomeStatement", 1, 2, statement),
                               har_entry("CD", 2, 2, {"staticData": {"cash": 11, "cd": 0, "rate": 3}}),
                               {"request": {"url": "https://cdn.example/x.png"}, "response": {"content": {}}}]}}
    responses = list(responses_from_har(har))
    assert [r.service for r in responses] == ["IncomeStatement", "CD"]
    assert responses[0].quarter == 1 and "x-xsrf-token" not in json.dumps([r.result for r in responses])
    views = _latest_views(responses)
    assert set(views) == {"IncomeStatement@Q1", "CD"}  # last quarter's report is kept apart
    actual = rc.actuals_from_views(views, 1)
    assert actual["income"]["rd"] == -77.0  # expense row signed like compare() expects


def test_pack_extras_and_merge_keep_what_a_capture_does_not_show() -> None:
    views = {
        "CostOfProduction": {"dynamicData": {"brands": [{"brandType": "A", "brandFeatures": ["c1", "c2"],
                                                         "cogsEstimates": [{"units": 90, "cost": 333.3},
                                                                           {"units": 270, "cost": 222.2}]}]}},
        "HireSalesPeople": {"staticData": {"regions": [{"hireCost": 71, "layOffCost": 13, "supportTrainCost": 5,
                                                        "segments": [{"segmentID": 1, "trainCost": 9}],
                                                        "cities": [{"annualCompensation": 1234}]}]}},
        "HireWebSalesPeople": {"staticData": {"regions": [{"regionID": 1, "regionName": "N", "opened": True,
                                                           "hireCost": 71, "layOffCost": 13}]}},
    }
    data = build_pack_dict(views)
    assert data["cost_estimates"][0]["points"] == [[90.0, 333.3], [270.0, 222.2]]
    assert data["modules"]["sales_force"] == {"hire_cost": 71.0, "severance_cost": 13.0}
    assert data["web_centers"] == [{"key": "R1", "region": "R1", "name": "N", "opened": True}]
    base = {"web_centers": [{"key": "R1", "region": "R1", "name": "N", "setup_cost": 4321, "lease_cost": 321,
                             "opened": False}], "stores": [{"key": "R1-C9", "region": "R1", "name": "X", "setup_cost": 1,
                                                            "lease_cost": 1, "opened": False}]}
    merged = merge_over_base(data, base)
    assert merged["web_centers"][0] == {"key": "R1", "region": "R1", "name": "N", "setup_cost": 4321, "lease_cost": 321,
                                        "opened": True}
    assert merged["stores"] == base["stores"]  # no store screen in this capture: kept


def test_curve_reproduces_its_own_rows_and_predicts_a_new_design() -> None:
    pack = pack_from_dict(synthetic_pack_with_table())
    bt_a, bt_b = pack.brand_type("A"), pack.brand_type("B")
    own = [pack.component("c1"), pack.component("c2")]
    for u in VOLUMES:
        got = curve_cost(pack, bt_a, own, u)
        assert got is not None and got.cost == pytest.approx(game_cost(u, 21 + 57), rel=1e-9)
        assert got.material_part + got.conversion_part == pytest.approx(got.cost)
    other = [pack.component("c1"), pack.component("c3")]  # not in the table: linear in material across designs
    material = sum(c.price for c in other)
    for u in VOLUMES:
        assert curve_cost(pack, bt_b, other, u).cost == pytest.approx(game_cost(u, material), rel=1e-6)
    between = curve_cost(pack, bt_a, own, 500.0)
    assert between.cost == pytest.approx(game_cost(500.0, 78), rel=0.02) and not between.extrapolated
    assert curve_cost(pack, bt_a, own, 9000.0).extrapolated
    check = validate(pack)
    assert check["leave_one_volume_out_max_abs_pct"] < 5


def test_spline_is_exact_at_knots_and_monotone_here() -> None:
    pts = [(u, game_cost(u, 100)) for u in VOLUMES]
    for u, v in pts:
        assert interpolate(pts, u)[0] == pytest.approx(v)
    grid = [interpolate(pts, u)[0] for u in range(90, 2431, 60)]
    assert all(a >= b for a, b in itertools.pairwise(grid))


def test_engine_uses_the_curve_at_the_produced_volume() -> None:
    pack = pack_from_dict(synthetic_pack_with_table())
    state = CompanyState.initial(pack)
    state.fixed_capacity_units = 40
    state.stores_open = [pack.stores[0].key]
    plan = Plan.from_dict({"brands": [{"name": "Alpha-1", "brand_type": "A", "components": ["c1", "c2"], "price": 700,
                                       "production": 270}]})
    _, report = advance(state, plan, pack)
    cost = report.lines["unit_cost[Alpha-1]"]
    assert cost.level == Level.ESTIMATED and cost.value == pytest.approx(game_cost(270, 78))
    assert report.lines["production_cost"].value == pytest.approx(270 * game_cost(270, 78))
    plain = load_pack(ROOT / "examples" / "synthetic")  # no table: the placeholder rule, unchanged
    _, report = advance(state, plan, plain)
    assert report.lines["unit_cost[Alpha-1]"].level == Level.PLACEHOLDER
    assert m.unit_cost(plain, plain.brand_type("A"), [plain.component("c1")], volume=100).level == Level.PLACEHOLDER


def test_reconcile_cli_refuses_a_public_output(tmp_path: Path) -> None:
    from marketplace_sim.cli import main

    with pytest.raises(SystemExit, match="private"):
        main(["reconcile", "--params", str(ROOT / "examples" / "synthetic"), "--har", "x.har", "--quarter", "1",
              "--plan", "x.yaml", "--out", str(tmp_path / "public" / "r.json")])
