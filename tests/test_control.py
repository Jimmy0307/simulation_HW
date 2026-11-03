"""Control plane tests (synthetic data only): spec parsing, overrides, events, determinism, sweeps, diff, HTML, MCP tools."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from marketplace_sim.cli import main as mpsim
from marketplace_sim.control import mcp_server
from marketplace_sim.control.diff import (
    diff_dirs,
    diff_packs,
    quarterly_snapshot,
    red_flags,
    render,
)
from marketplace_sim.control.events import apply_events, validate
from marketplace_sim.control.html import render_results
from marketplace_sim.control.runner import build_competitor, run_scenario
from marketplace_sim.control.spec import (
    CompetitorSpec,
    EventSpec,
    Override,
    apply_overrides,
    apply_path,
    load_spec,
    spec_from_dict,
)
from marketplace_sim.control.sweep import expand, load_sweep, run_sweep, worst

ROOT = Path(__file__).parents[1]
SYNTHETIC = ROOT / "examples" / "synthetic"
SCENARIOS = ROOT / "examples" / "scenarios"
DEMO = ROOT / "examples" / "demo-control"


@pytest.fixture()
def raw_pack() -> dict:  # type: ignore[type-arg]
    data: dict = json.loads((SYNTHETIC / "pack.json").read_text(encoding="utf-8"))  # type: ignore[type-arg]
    return data


# --- spec parsing ---------------------------------------------------------------------------------------------------

def test_all_templates_parse_and_resolve() -> None:
    names = set()
    for path in sorted(SCENARIOS.glob("*.yaml")):
        spec = load_spec(path)
        names.add(spec.name)
        assert spec.resolve(spec.base_params).joinpath("pack.json").exists()
        for event in spec.events:
            validate(event)
    assert {"baseline", "cost-rise", "demand-decline", "price-war", "combined-shock"} <= names


def test_spec_rejects_bad_override_op() -> None:
    with pytest.raises((ValueError, KeyError, TypeError)):
        spec_from_dict({"name": "x", "base_params": ".", "overrides": [{"path": "a"}]}, ".")


def test_fingerprint_changes_with_content() -> None:
    a = spec_from_dict({"name": "x", "base_params": "p", "seed": 1}, ".")
    b = spec_from_dict({"name": "x", "base_params": "p", "seed": 2}, ".")
    assert a.fingerprint("{}") != b.fingerprint("{}")
    assert a.fingerprint("{}") == copy.deepcopy(a).fingerprint("{}")


# --- overrides ------------------------------------------------------------------------------------------------------

def test_path_syntax(raw_pack: dict) -> None:  # type: ignore[type-arg]
    data = copy.deepcopy(raw_pack)
    assert apply_path(data, "stores[key=N1-Eastmere].setup_cost", lambda v: 1) == 1
    assert next(s for s in data["stores"] if s["key"] == "N1-Eastmere")["setup_cost"] == 1
    assert apply_path(data, "markets[*].segments.*.wtp", lambda v: v) == 9
    assert apply_path(data, "finance.cd_rate_annual_percent", lambda v: v + 1) == 1


def test_overrides_respect_quarter_window_and_reject_unknown_paths(raw_pack: dict) -> None:  # type: ignore[type-arg]
    o = Override("finance.cd_rate_annual_percent", "add", 1.0, from_quarter=2, to_quarter=3)
    assert apply_overrides(raw_pack, [o], 1)[0]["finance"]["cd_rate_annual_percent"] == raw_pack["finance"]["cd_rate_annual_percent"]
    assert apply_overrides(raw_pack, [o], 2)[0]["finance"]["cd_rate_annual_percent"] == pytest.approx(5.4)
    scaled = apply_overrides(raw_pack, [Override("capacity_options[*].cost", "scale", 2.0)], 1)[0]
    assert [c["cost"] for c in scaled["capacity_options"]] == [c["cost"] * 2 for c in raw_pack["capacity_options"]]
    with pytest.raises(ValueError):
        apply_overrides(raw_pack, [Override("no.such.path", "set", 1)], 1)


# --- events ---------------------------------------------------------------------------------------------------------

def test_each_event_type_has_its_effect(raw_pack: dict) -> None:  # type: ignore[type-arg]
    data, adj = apply_events(raw_pack, [EventSpec("cost_shock", 1, 0.1, "capacity")], 1)
    assert data["capacity_options"][1]["cost"] == pytest.approx(raw_pack["capacity_options"][1]["cost"] * 1.1)
    data, _ = apply_events(raw_pack, [EventSpec("demand_shock", 1, -0.5, "2")], 1)
    assert data["markets"][0]["segments"]["2"]["size_12m"] == pytest.approx(raw_pack["markets"][0]["segments"]["2"]["size_12m"] / 2)
    assert data["markets"][0]["segments"]["1"]["size_12m"] == raw_pack["markets"][0]["segments"]["1"]["size_12m"]
    data, _ = apply_events(raw_pack, [EventSpec("rate_change", 1, -1.0, "cd")], 1)
    assert data["finance"]["cd_rate_annual_percent"] == pytest.approx(3.4)
    _, adj = apply_events(raw_pack, [EventSpec("supply_disruption", 1, 0.25, "capacity")], 1)
    assert adj.capacity_factor == pytest.approx(0.75)
    _, adj = apply_events(raw_pack, [EventSpec("competitor_price_cut", 1, -0.2, "*")], 1)
    assert adj.rival_price_factor["*"] == pytest.approx(0.8)
    assert adj.labels == ["competitor_price_cut(*, -0.2)"]


def test_events_compose_and_respect_duration(raw_pack: dict) -> None:  # type: ignore[type-arg]
    events = [EventSpec("cost_shock", 2, 0.1, "capacity", duration=2), EventSpec("cost_shock", 3, 0.1, "capacity")]
    base = raw_pack["capacity_options"][1]["cost"]
    assert apply_events(raw_pack, events, 1)[0]["capacity_options"][1]["cost"] == base
    assert apply_events(raw_pack, events, 2)[0]["capacity_options"][1]["cost"] == pytest.approx(base * 1.1)
    data, adj = apply_events(raw_pack, events, 3)
    assert data["capacity_options"][1]["cost"] == pytest.approx(base * 1.21) and len(adj.labels) == 2
    assert apply_events(raw_pack, events, 4)[0]["capacity_options"][1]["cost"] == base


def test_invalid_events_are_rejected() -> None:
    for bad in (EventSpec("meteor", 1, 1.0), EventSpec("cost_shock", 1, 0.1, "moon"),
                EventSpec("supply_disruption", 1, 1.5, "capacity")):
        with pytest.raises(ValueError):
            validate(bad)


def test_events_are_labelled_in_reports() -> None:
    result = run_scenario(load_spec(SCENARIOS / "cost-rise.yaml")).to_dict()
    q3 = next(q for q in result["quarters"] if q["quarter"] == 3)
    assert "machine price spike" in q3["events"]
    assert any(n.startswith("event: ") for n in q3["notes"])
    assert result["summary"]["quarters_with_events"] == [2, 3, 4]


def test_cost_shock_moves_only_the_verified_capex_line() -> None:
    base = run_scenario(load_spec(SCENARIOS / "baseline.yaml")).to_dict()
    shock = run_scenario(load_spec(DEMO / "scenario.yaml")).to_dict()
    b3, s3 = base["quarters"][2]["lines"], shock["quarters"][2]["lines"]
    assert s3["capex_capacity"]["value"] == pytest.approx(b3["capex_capacity"]["value"] * 1.15)
    assert s3["capex_capacity"]["level"] == "verified"
    assert base["quarters"][1]["lines"] == shock["quarters"][1]["lines"]


# --- competitors ----------------------------------------------------------------------------------------------------

def test_replay_requires_private_or_synthetic_panel(tmp_path: Path) -> None:
    spec = spec_from_dict({"name": "x", "base_params": str(SYNTHETIC)}, str(tmp_path))
    panel = {"quarters": {"1": [{"firm": "r", "brand": "b", "segment_id": "1", "price": 700, "markets": ["N1-Northwick"]}]}}
    (tmp_path / "panel.json").write_text(json.dumps(panel), encoding="utf-8")
    with pytest.raises(ValueError):
        build_competitor(CompetitorSpec("r", "replay", {"panel": "panel.json"}), spec)
    (tmp_path / "panel.json").write_text(json.dumps({**panel, "synthetic": True}), encoding="utf-8")
    bot = build_competitor(CompetitorSpec("r", "replay", {"panel": "panel.json"}), spec)
    assert bot is not None


# --- determinism ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["baseline", "price-war", "combined-shock"])
def test_same_spec_and_seed_give_identical_results(name: str) -> None:
    spec = load_spec(SCENARIOS / f"{name}.yaml")
    a, b = run_scenario(spec).to_dict(), run_scenario(load_spec(SCENARIOS / f"{name}.yaml")).to_dict()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_seed_changes_random_rivals_only() -> None:
    spec = load_spec(SCENARIOS / "price-war.yaml")
    a = run_scenario(spec).to_dict()
    spec.seed += 1
    b = run_scenario(spec).to_dict()
    assert a["fingerprint"] != b["fingerprint"]
    assert a["quarters"][0]["lines"]["capex_capacity"] == b["quarters"][0]["lines"]["capex_capacity"]


# --- sweep ----------------------------------------------------------------------------------------------------------

def test_sweep_grid_expansion_and_worst() -> None:
    sweep = load_sweep(DEMO / "sweep.yaml")
    pairs = expand(sweep)
    assert len(pairs) == 18 and len({s.name for _, s in pairs}) == 18
    assert [a for a, _ in pairs] == [a for a, _ in expand(sweep)]
    result = run_sweep(sweep)
    assert result["schema"] == "marketplace-sim/sweep-result@1"
    w = worst(result["rows"], 3)
    assert w[0]["objective"] <= w[1]["objective"] <= w[2]["objective"]
    assert w[0]["assignment"]["capacity_cost"] == 1.25
    assert result["sensitivity"][0]["variable"] == "capacity_cost"
    assert all(len(r["fingerprint"]) == 16 for r in result["rows"])


def test_sweep_sample_mode_is_seeded(tmp_path: Path) -> None:
    text = (DEMO / "sweep.yaml").read_text(encoding="utf-8").replace("mode: grid", "mode: sample\nsamples: 5\nseed: 11")
    (tmp_path / "s.yaml").write_text(text.replace("base_scenario: scenario.yaml",
                                                   f"base_scenario: {(DEMO / 'scenario.yaml').as_posix()}"), encoding="utf-8")
    sweep = load_sweep(tmp_path / "s.yaml")
    first = [a for a, _ in expand(sweep)]
    assert len(first) == 5 and first == [a for a, _ in expand(sweep)]


# --- diff -----------------------------------------------------------------------------------------------------------

def test_params_diff_flags_verified_modules() -> None:
    changes = diff_dirs(SYNTHETIC, DEMO / "pack-v2")
    modules = {c.module for c in changes if c.needs_reverification}
    assert any("EXP-01" in m for m in modules) and any("EXP-02" in m for m in modules)
    assert changes[0].needs_reverification
    assert "RED FLAG" in "\n".join(red_flags(changes))
    public = render(changes, include_values=False)
    assert "4321" not in public and "4011" not in public
    assert "4011" in render(changes, include_values=True)
    assert diff_packs({"a": 1}, {"a": 1}) == []


def test_quarterly_snapshot_is_private_only(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        quarterly_snapshot(tmp_path, "Q1")
    model = tmp_path / "private" / "model"
    model.mkdir(parents=True)
    (model / "pack.json").write_text((SYNTHETIC / "pack.json").read_text(encoding="utf-8"), encoding="utf-8")
    assert quarterly_snapshot(model, "Q1") == ([], None)
    (model / "pack.json").write_text((DEMO / "pack-v2" / "pack.json").read_text(encoding="utf-8"), encoding="utf-8")
    changes, previous = quarterly_snapshot(model, "Q2")
    assert previous == "Q1" and changes and (model / "diffs" / "Q2-vs-Q1.md").exists()


# --- HTML + CLI + MCP -----------------------------------------------------------------------------------------------

def test_html_report_is_self_contained() -> None:
    page = render_results([run_scenario(load_spec(DEMO / "scenario.yaml")).to_dict()], "demo")
    assert page.startswith("<!doctype html>") and "<svg" in page and "⚑" in page
    assert "<script" not in page and "http://" not in page and "https://" not in page


def test_cli_scenario_sweep_and_diff(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mpsim(["scenario", "new", str(tmp_path / "mine.yaml"), "--params", str(SYNTHETIC)])
    assert load_spec(tmp_path / "mine.yaml").name == "mine"
    mpsim(["scenario", "run", str(DEMO / "scenario.yaml"), "--out", str(tmp_path / "out")])
    assert (tmp_path / "out" / "demo-cost-shock.html").exists()
    mpsim(["sweep", "run", str(DEMO / "sweep.yaml"), "--out", str(tmp_path / "out")])
    capsys.readouterr()
    mpsim(["sweep", "worst", str(tmp_path / "out" / "demo-stress.sweep.json"), "--top", "3"])
    assert capsys.readouterr().out.count("demo-stress-") == 3
    mpsim(["params", "diff", str(SYNTHETIC), str(DEMO / "pack-v2")])
    assert "re-verification" in capsys.readouterr().out


def test_cli_refuses_real_outputs_outside_private(tmp_path: Path) -> None:
    pack = json.loads((SYNTHETIC / "pack.json").read_text(encoding="utf-8"))
    pack["provenance"] = "private"
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "pack.json").write_text(json.dumps(pack), encoding="utf-8")
    (tmp_path / "s.yaml").write_text("name: s\nbase_params: p\nhorizon: 1\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        mpsim(["scenario", "run", str(tmp_path / "s.yaml"), "--out", str(tmp_path / "out")])


def test_mcp_tool_functions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(mcp_server, "ROOT", ROOT)
    listed = mcp_server.tool_list_scenarios("examples/scenarios")
    assert {"baseline", "price-war"} <= {s["name"] for s in listed}
    out = mcp_server.tool_run_scenario("examples/scenarios/baseline.yaml")
    assert out["summary"]["weakest_level"]["capex_capacity"] == "verified"
    with pytest.raises(ValueError):
        mcp_server.tool_run_scenario("../outside.yaml")


def test_event_quarter_alias() -> None:
    a = spec_from_dict({"name": "x", "base_params": "p", "events": [{"type": "cost_shock", "from_quarter": 3}]}, ".")
    b = spec_from_dict({"name": "x", "base_params": "p", "events": [{"type": "cost_shock", "quarter": 3}]}, ".")
    assert a.events == b.events and a.events[0].active(3) and not a.events[0].active(2)


def test_policy_sweep_uses_portable_relative_paths() -> None:
    sweep = load_sweep(DEMO / "sweep-plans.yaml")
    pairs = expand(sweep)
    assert len(pairs) == 18
    policy = pairs[0][1].our_policy
    assert not Path(policy["default"]).is_absolute() and policy["default"].endswith("a-cautious.yaml")
    result = run_sweep(sweep)
    assert result["sensitivity"][0]["variable"] == "plan"
