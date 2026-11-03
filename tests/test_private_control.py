"""Private control-plane check: real pack through run_scenario / run_sweep. Skipped unless private evidence exists.

Verified engine lines produced via the control plane must equal the measured server results (residual 0).
Reads and writes only under evidence/private (never committed) and prints no values.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from marketplace_sim.control.runner import run_scenario
from marketplace_sim.control.spec import load_spec, spec_from_dict
from marketplace_sim.control.sweep import load_sweep, run_sweep

P = Path(__file__).parents[1] / "evidence" / "private"
NEEDED = [P / "model" / "pack.json", P / "exp-01" / "experiment_values.json", P / "exp-02" / "experiment_values.json",
          P / "auto" / "exp03_rows.json", P / "auto" / "exp04_rows.json", P / "scenarios" / "real-q1.yaml",
          P / "scenarios" / "real-q1-sweep.yaml"]
pytestmark = pytest.mark.skipif(not all(p.exists() for p in NEEDED), reason="private evidence not present")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _q1(tmp_path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    spec = spec_from_dict({"name": "private-check", "base_params": str(P / "model"), "horizon": 1,
                           "our_policy": {"type": "fixed", "plans": {1: str(plan_path)}}}, str(tmp_path))
    lines: dict[str, Any] = run_scenario(spec).to_dict()["quarters"][0]["lines"]
    return lines


def test_capacity_and_cd_via_control_plane(tmp_path: Path) -> None:
    for row in [r for r in _load(P / "exp-02" / "experiment_values.json") if r["method"] == "calculate"]:
        line = _q1(tmp_path, {"capacity_increase": row["decisions_sent"]["increase"]})["capex_capacity"]
        assert line["value"] == row["calculate_result"]["total"] and line["level"] == "verified"
    for row in [r for r in _load(P / "exp-01" / "experiment_values.json") if r["method"] == "calculate" and r["check_ok"]]:
        lines = _q1(tmp_path, {"cd": {"deposit": row["decisions_sent"]["deposit"], "withdraw": row["decisions_sent"]["withdraw"]}})
        assert lines["cd_balance"]["value"] == row["calculate_result"]["cd"]
        assert lines["cd_interest"]["value"] == pytest.approx(row["calculate_result"]["interest"], abs=0)
        assert lines["cd_interest"]["level"] == "verified"


@pytest.mark.parametrize(("rows_file", "field", "line"), [("exp03_rows.json", "open_stores", "store_setup"),
                                                           ("exp04_rows.json", "open_web_centers", "web_center_setup")])
def test_opening_via_control_plane(tmp_path: Path, rows_file: str, field: str, line: str) -> None:
    for row in _load(P / "auto" / rows_file):
        keys = [f"R{k[0]}-C{k[1]}" if isinstance(k, list) else f"R{k}" for k in row["on"]]
        result = _q1(tmp_path, {field: keys})[line]
        assert result["value"] == row["calc"]["total"] and result["level"] == "verified"


def test_private_scenario_and_sweep_are_deterministic_and_keep_levels() -> None:
    spec = load_spec(P / "scenarios" / "real-q1.yaml")
    a, b = run_scenario(spec).to_dict(), run_scenario(load_spec(P / "scenarios" / "real-q1.yaml")).to_dict()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["summary"]["weakest_level"]["capex_capacity"] == "verified"
    result = run_sweep(load_sweep(P / "scenarios" / "real-q1-sweep.yaml"))
    assert len(result["rows"]) == 12
    assert all(r["summary"]["weakest_level"]["capex_capacity"] == "verified" for r in result["rows"])
