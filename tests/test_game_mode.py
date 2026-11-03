"""Game mode: a thin layer over the engine and control plane. Every number must equal a direct engine call."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from marketplace_sim import modules as m
from marketplace_sim.api import game as gm
from marketplace_sim.api import service as svc
from marketplace_sim.api.app import create_app
from marketplace_sim.control.runner import _PriceScaledBot, build_competitor
from marketplace_sim.control.spec import CompetitorSpec, ScenarioSpec
from marketplace_sim.engine import CompanyState, Plan, advance
from marketplace_sim.pack import load_pack

ROOT = Path(__file__).parents[1]
PRIVATE_PACK = ROOT / "evidence" / "private" / "model" / "pack.json"
THREE = [{"difficulty": "conservative"}, {"difficulty": "normal"}, {"difficulty": "aggressive"}]
# The synthetic full turn from the task: one product, one store, a price; then end the quarter.
TURN = {"name": "turn", "capacity_increase": 9, "open_stores": ["N1-Northwick"],
        "brands": [{"name": "Bike-1", "brand_type": "A", "price": 699, "production": 0, "advertising": 10000,
                    "components": ["c1", "c2"]}]}


def _demo_plan(name: str) -> dict[str, Any]:
    data = yaml.safe_load((svc.SYNTHETIC_PLANS / name).read_text(encoding="utf-8"))
    return {"name": data.get("name", name), **data}


def _direct(plans: list[dict[str, Any]], opponents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reference: the engine called directly with control-plane bots, no API in between."""
    pack = load_pack(svc.SYNTHETIC_PACK)
    scenario = ScenarioSpec(name="ref", base_params=str(svc.SYNTHETIC_PACK))
    rivals = [build_competitor(CompetitorSpec(f"rival-{i + 1}", gm.DIFFICULTIES[o["difficulty"]]["strategy"],
                                              dict(gm.DIFFICULTIES[o["difficulty"]]["params"])), scenario)
              for i, o in enumerate(opponents)]
    state = CompanyState.initial(pack)
    out = []
    for plan in plans:
        state, report = advance(state, Plan.from_dict(plan), pack, competitors=rivals, seed=0)
        out.append(report.to_dict()["lines"])
    return out


def _same(api_lines: dict[str, Any], ref_lines: dict[str, Any]) -> None:
    assert set(api_lines) == set(ref_lines)
    for key, ref in ref_lines.items():
        assert api_lines[key]["value"] == ref["value"], key
        assert api_lines[key]["level"] == ref["level"], key


def test_setup_reads_everything_from_the_pack() -> None:
    session = svc.Session()
    doc = gm.setup(session)
    pack = session.pack
    assert doc["theme"] == {"product": "自行車", "unit": "輛", "icon": "bicycle"}
    assert doc["is_private"] is False and doc["source"] == "synthetic"
    assert [b["code"] for b in doc["brand_types"]] == [b.code for b in pack.brand_types]
    for row, bt in zip(doc["brand_types"], pack.brand_types, strict=True):
        assert row["components"] == [c.id for c in pack.components if m.compatible(c, bt)]
        assert row["default_components"] == [c.id for c in m.default_components(pack, bt)]
    cities = [c for r in doc["regions"] for c in r["cities"]]
    assert {c["key"] for c in cities} == {s.key for s in pack.stores}
    city = cities[0]
    assert city["store"]["setup_cost"]["level"] == "verified" and city["store"]["setup_cost"]["uncalibrated"] is False
    assert city["store"]["lease_cost"]["level"] == "placeholder" and city["store"]["lease_cost"]["uncalibrated"] is True
    assert {s["wtp"]["level"] for s in city["segments"]} == {"derived"}
    assert doc["capacity_units_per_quarter"]["level"] == "verified"
    assert doc["capacity_units_per_quarter"]["value"] == m.quarterly_capacity(pack, 0).value
    assert [o["cost"]["value"] for o in doc["capacity_options"]] == [o.cost for o in pack.capacity_options]
    assert doc["max_opponents"] == 6 and {d["id"] for d in doc["difficulties"]} == {"conservative", "normal", "aggressive"}
    assert doc["replay"]["available"] is False and "private" in doc["replay"]["reason"]
    assert [p["id"] for p in doc["presets"]] == [p["id"] for p in svc.plan_presets(session)["presets"]]


def test_difficulties_map_onto_existing_bots() -> None:
    session = svc.Session()
    gm.start(session, {"opponents": THREE})
    bots = svc.session_competitors(session)
    assert bots is not None and len(bots) == 3
    assert isinstance(bots[0], _PriceScaledBot) and isinstance(bots[0].inner, m.BaselineBot) and bots[0].factor == 1.1
    assert isinstance(bots[1], m.BaselineBot)
    assert isinstance(bots[2], _PriceScaledBot) and isinstance(bots[2].inner, m.RandomBot) and bots[2].factor == 0.85


@pytest.mark.parametrize("count", [1, 3, 6])
def test_opponent_count_reaches_the_engine(count: int) -> None:
    session = svc.Session()
    opponents = [{"difficulty": "normal"}] * count
    gm.start(session, {"opponents": opponents})
    svc.play(session, _demo_plan("q1.yaml"))
    lines = svc.play(session, _demo_plan("q2.yaml"))["report"]["lines"]
    shares = {k: v for k, v in lines.items() if k.startswith("rival_share[")}
    assert len(shares) == count
    assert all(v["level"] == "literature" and v["uncalibrated"] for v in shares.values())
    assert abs(lines["market_share"]["value"] + sum(v["value"] for v in shares.values()) - 1) < 1e-9


def test_full_turn_matches_a_direct_engine_call() -> None:
    session = svc.Session()
    gm.start(session, {"source": "synthetic", "opponents": THREE, "objective": "讓期末現金最大化"})
    preview = svc.preview(session, TURN)["report"]["lines"]
    played = svc.play(session, TURN)["report"]["lines"]
    second = svc.play(session, _demo_plan("q2.yaml"))["report"]["lines"]
    reference = _direct([TURN, _demo_plan("q2.yaml")], THREE)
    _same(preview, reference[0])
    _same(played, reference[0])
    _same(second, reference[1])
    assert played["store_setup"]["level"] == "verified" and played["store_setup"]["uncalibrated"] is False
    assert played["unit_cost[Bike-1]"]["level"] == "placeholder" and played["unit_cost[Bike-1]"]["uncalibrated"]
    assert session.game_meta is not None and session.game_meta["objective"] == "讓期末現金最大化"
    assert gm.state_view(session)["state"]["quarter"] == 3


def test_new_game_and_pack_switch_restore_default_bots() -> None:
    session = svc.Session()
    gm.start(session, {"opponents": THREE})
    svc.new_game(session)
    assert session.competitors is None and session.game_meta is None
    gm.start(session, {"opponents": THREE})
    svc.load_pack_into(session, "synthetic")
    assert session.competitors is None


@pytest.mark.parametrize("body", [{"opponents": []}, {"opponents": [{"difficulty": "normal"}] * 7},
                                  {"opponents": [{"difficulty": "brutal"}]}, {"opponents": THREE, "source": "mars"},
                                  {"replay": True}])
def test_start_rejects_bad_requests(body: dict[str, Any]) -> None:
    with pytest.raises(svc.ApiError):
        gm.start(svc.Session(), body)


def test_api_endpoints_full_flow() -> None:
    client = TestClient(create_app(svc.Session()))
    setup = client.get("/api/game-mode/setup").json()
    assert setup["theme"]["icon"] == "bicycle" and setup["is_private"] is False
    started = client.post("/api/game-mode/start", json={"source": "synthetic", "opponents": THREE}).json()
    assert [o["label"] for o in started["game"]["opponents"]] == ["保守", "普通", "激進"]
    preview = client.post("/api/game/preview", json=TURN).json()["report"]["lines"]
    played = client.post("/api/game/play", json=TURN).json()
    _same(preview, _direct([TURN], THREE)[0])
    _same(played["report"]["lines"], _direct([TURN], THREE)[0])
    after = client.get("/api/game-mode/setup").json()
    assert after["state"]["quarter"] == 2 and "N1-Northwick" in after["state"]["stores_open"]
    assert client.post("/api/game-mode/start", json={"opponents": []}).status_code == 400


def test_demo_bundle_game_script_is_synthetic_and_engine_made() -> None:
    doc = json.loads((ROOT / "frontend" / "public" / "demo" / "gamemode.json").read_text(encoding="utf-8"))
    assert doc["start"]["is_private"] is False and doc["config"]["source"] == "synthetic"
    plans = [step["plan"] for step in doc["steps"]]
    reference = _direct(plans, doc["config"]["opponents"])
    for step, ref in zip(doc["steps"], reference, strict=True):
        _same(step["report"]["lines"], ref)
        _same(step["preview"]["lines"], ref)
        assert len([k for k in step["report"]["lines"] if k.startswith("rival_share[")]) == 3


@pytest.mark.skipif(not PRIVATE_PACK.exists(), reason="private pack not present")
def test_private_source_runs_and_stays_private() -> None:
    before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    session = svc.Session()
    doc = gm.start(session, {"source": "private", "opponents": THREE})
    assert doc["is_private"] is True and doc["source"] == "private"
    assert doc["replay"]["available"] is False
    plan = {"name": "p", "brands": [{"name": "Bike-1", "brand_type": doc["brand_types"][0]["code"], "price": 1,
                                     "production": 0}]}
    report = svc.play(session, plan)
    assert report["is_private"] is True and len([k for k in report["report"]["lines"] if k.startswith("rival_share[")]) == 3
    after = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    assert after == before  # nothing written into tracked or untracked repo files
