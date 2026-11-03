"""Local API: thin layer over the engine. Synthetic data only (a private-pack test runs only if private data exists)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from marketplace_sim.api import service as svc
from marketplace_sim.api.app import create_app
from marketplace_sim.api.export import build_bundle, export_demo
from marketplace_sim.engine import CompanyState, Plan, advance
from marketplace_sim.pack import load_pack

ROOT = Path(__file__).parents[1]
Q1 = {"name": "q1", "stock_issue": [{"shares": 48611, "price": 31}], "capacity_increase": 18,
      "open_stores": ["N1-Northwick", "N1-Eastmere"], "cd": {"deposit": 99173, "withdraw": 0},
      "brands": [{"name": "Alpha-1", "brand_type": "A", "price": 0, "production": 0}]}
LEVELS = {"verified", "derived", "estimated", "literature", "placeholder"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(svc.Session()))


def _assert_levels(lines: dict[str, Any]) -> None:
    assert lines
    for name, line in lines.items():
        assert line["level"] in LEVELS, name
        assert line["uncalibrated"] == (line["level"] in {"literature", "placeholder"})
        assert line["chain"] and line["chain"][0]["level"] in LEVELS


def test_pack_defaults_to_synthetic_and_is_not_private(client: TestClient) -> None:
    info = client.get("/api/pack").json()
    assert info["is_private"] is False and info["source"] == "synthetic" and info["demand_model"] == "literature"
    assert client.post("/api/pack", json={"source": "private", "path": str(ROOT / "examples" / "synthetic")}).status_code == 400
    assert client.post("/api/pack", json={"source": "nope"}).status_code == 400


def test_play_matches_the_engine_and_carries_levels(client: TestClient) -> None:
    client.post("/api/game/new", json={})
    body = client.post("/api/game/play", json=Q1).json()
    assert body["is_private"] is False
    _assert_levels(body["report"]["lines"])
    pack = load_pack(ROOT / "examples" / "synthetic")
    _, report = advance(CompanyState.initial(pack), Plan.from_dict(Q1, name="q1"), pack)
    assert body["report"]["lines"]["cash_end"]["value"] == report.lines["cash_end"].value  # single engine
    assert body["report"]["lines"]["capex_capacity"]["level"] == "verified"
    assert client.get("/api/game").json()["state"]["quarter"] == 2


def test_compare_preview_and_presets(client: TestClient) -> None:
    presets = client.get("/api/plans").json()
    assert presets["is_private"] is False and len(presets["presets"]) == 3
    compared = client.post("/api/compare", json={"plans": [p["plan"] for p in presets["presets"]]}).json()
    assert len(compared["reports"]) == 3
    for report in compared["reports"]:
        _assert_levels(report["lines"])
    preview = client.post("/api/game/preview", json=presets["presets"][0]["plan"]).json()
    _assert_levels(preview["report"]["lines"])


def test_scenario_events_and_competitors(client: TestClient) -> None:
    templates = client.get("/api/scenarios").json()["templates"]
    spec = next(t["spec"] for t in templates if t["id"] == "price-war")
    body = client.post("/api/scenario/run", json=spec).json()
    assert body["is_private"] is False
    quarters = body["result"]["quarters"]
    assert any(q["events"] for q in quarters)
    for q in quarters:
        _assert_levels(q["lines"])
    assert body["result"]["summary"]["weakest_level"]["revenue"] == "literature"
    assert {e["type"] for e in client.get("/api/events").json()["types"]} >= {"cost_shock", "competitor_price_cut"}
    bad = {**spec, "events": [{"type": "meteor", "from_quarter": 1}]}
    assert client.post("/api/scenario/run", json=bad).status_code == 400


def test_sweep_worst_and_caveat(client: TestClient) -> None:
    sweeps = client.get("/api/sweeps").json()["sweeps"]
    sweep = next(s["sweep"] for s in sweeps if s["id"] == "sweep-demand")
    body = client.post("/api/sweep/run", json=sweep).json()
    assert body["is_private"] is False and body["demand_level"] == "literature" and body["caveat"]
    worst = client.get("/api/sweep/worst", params={"top": 3}).json()
    assert len(worst["worst"]) == 3 and worst["caveat"]


def test_diff_and_levels(client: TestClient) -> None:
    packs = client.get("/api/packs").json()["packs"]
    body = client.post("/api/diff", json={"old": packs[0]["path"], "new": packs[1]["path"]}).json()
    assert body["is_private"] is False and body["values_included"] is True
    assert any(c["needs_reverification"] for c in body["changes"]) and body["red_flags"]
    levels = client.get("/api/levels").json()
    assert levels["order"] == ["verified", "derived", "estimated", "literature", "placeholder"]
    explained = client.get("/api/explain/market_share").json()
    assert explained["level"] == "literature" and len(explained["chain"]) > 1


def test_demo_export_is_synthetic_and_value_free(tmp_path: Path) -> None:
    result = export_demo(str(tmp_path / "demo"))
    assert result["is_private"] is False
    manifest = json.loads((tmp_path / "demo" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["provenance"] == "synthetic" and manifest["is_private"] is False
    text = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "demo").glob("*.json"))
    assert '"is_private": true' not in text and str(ROOT) not in text and "evidence/private" not in text
    with pytest.raises(svc.ApiError):
        export_demo(str(tmp_path / "private" / "demo"))
    # Real values: the publication gate's detectors on the exported bundle (runs only if private reference exists).
    from marketplace_sysid.security.value_leak import load_real_values, scan_file_text

    private = ROOT / "evidence" / "private"
    real = load_real_values(private / "parameters" / "values.json", private / "model" / "pack.json")
    if not real.empty:
        for path in (tmp_path / "demo").glob("*.json"):
            assert scan_file_text(path.name, path.read_text(encoding="utf-8"), real) == []


def test_committed_demo_bundle_is_current() -> None:
    bundle = build_bundle()
    for key, value in bundle.items():
        committed = ROOT / "frontend" / "public" / "demo" / f"{key}.json"
        assert committed.exists(), f"run: python -m marketplace_sim.api.export ({key}.json missing)"
        assert json.loads(committed.read_text(encoding="utf-8")) == json.loads(json.dumps(value)), key


@pytest.mark.skipif(not (ROOT / "evidence" / "private" / "model" / "pack.json").exists(), reason="no private pack")
def test_private_pack_is_flagged(client: TestClient) -> None:
    info = client.post("/api/pack", json={"source": "private"}).json()
    assert info["is_private"] is True and info["source"] == "private"
    client.post("/api/game/new", json={})
    body = client.post("/api/game/play", json={"capacity_increase": 0}).json()
    assert body["is_private"] is True
    session = svc.Session()
    svc.load_pack_into(session, "private")
    session.state, session.save_path = CompanyState.initial(session.pack), ROOT / "outputs" / "not-private-save.json"
    with pytest.raises(svc.ApiError):
        svc.save_game(session)  # private results are never written outside a directory named private


def test_api_binds_loopback_only(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    from marketplace_sim.api import __main__ as entry

    monkeypatch.setattr(sys, "argv", ["mpsim-api", "--host", "0.0.0.0"])
    with pytest.raises(SystemExit):
        entry.main()
