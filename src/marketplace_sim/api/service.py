"""Thin service layer behind the local web API. Every function calls the existing engine or control plane.

No computation lives here: decoration only (source chains and the "uncalibrated" flag come from the metrics registry
and the level of each Tagged number the engine produced). Responses always carry ``is_private``.
Nothing is written into the repository except the synthetic demo export (``export.py``); results built from a private
pack are only returned to the local caller, or written under a directory named ``private`` when explicitly saved.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from marketplace_sim import modules as m
from marketplace_sim.control import events as ev
from marketplace_sim.control.diff import diff_dirs, red_flags
from marketplace_sim.control.runner import build_competitor
from marketplace_sim.control.runner import run_scenario as _run_scenario
from marketplace_sim.control.spec import CompetitorSpec, ScenarioSpec, spec_from_dict
from marketplace_sim.control.sweep import run_sweep as _run_sweep
from marketplace_sim.control.sweep import sweep_from_dict
from marketplace_sim.control.sweep import worst as _worst
from marketplace_sim.engine import CompanyState, Plan, Report, advance
from marketplace_sim.metrics import METRICS, chain, lookup
from marketplace_sim.pack import ParamPack, load_pack
from marketplace_sim.provenance import Level

ROOT = Path(__file__).resolve().parents[3]
SYNTHETIC_PACK = ROOT / "examples" / "synthetic"
SYNTHETIC_SCENARIOS = ROOT / "examples" / "scenarios"
SYNTHETIC_SWEEPS = ROOT / "examples" / "demo-control"
SYNTHETIC_PLANS = ROOT / "examples" / "demo"
PRIVATE_ROOT = ROOT / "evidence" / "private"
UNCALIBRATED = {Level.LITERATURE, Level.PLACEHOLDER, Level.HEURISTIC}
LEVEL_MEANING = {
    Level.VERIFIED: "Reproduced against measured server results with zero residual.",
    Level.DERIVED: "Follows directly from published parameters (exact identity).",
    Level.ESTIMATED: "Fitted to this game's data and validated on a held-out quarter.",
    Level.LITERATURE: "Functional form from published literature; coefficients not calibrated on this game. Not a forecast.",
    Level.PLACEHOLDER: "Illustrative, uncalibrated. Not a forecast.",
    Level.HEURISTIC: "Practice rule from general business sense (business module): no literature, no calibration. Direction only; never a forecast.",
}


class ApiError(ValueError):
    """A request the API refuses (bad input or a boundary rule)."""


def _is_private_path(path: Path) -> bool:
    return any(part.casefold() == "private" for part in path.resolve().parts)


# --- decoration (presentation metadata only) -------------------------------------------------------------------------

# Business-module lines: only shown in a source chain when the report has them (the module was active).
_MODULE_LINES = {"ad_efficiency", "effective_advertising", "selling_effort"}


def decorate_line(name: str, line: dict[str, Any], present: set[str] | None = None) -> dict[str, Any]:
    level = Level[str(line["level"]).upper()]
    return {**line, "mark": level.mark, "uncalibrated": level in UNCALIBRATED,
            "chain": [{"metric": c.name, "level": c.level.label, "formula": c.formula, "evidence": c.evidence,
                       "note": c.note} for c in chain(name, present)]}


def decorate_lines(lines: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    bases = {n.split("[", 1)[0] for n in lines}
    # Upstream rows a report never carries as lines (e.g. unit_cost is per brand) stay; only module rows are filtered.
    present = {name for name in _all_metric_bases() if name in bases or not _is_module_metric(name)}
    return {name: decorate_line(name, line, present) for name, line in lines.items()}


def _all_metric_bases() -> set[str]:
    return {key.split("[", 1)[0] for key in METRICS}


def _is_module_metric(base: str) -> bool:
    return base in _MODULE_LINES or base.startswith("sales_force_")


def report_dict(report: Report) -> dict[str, Any]:
    data = report.to_dict()
    data["lines"] = decorate_lines(data["lines"])
    return data


def decorate_result(result: dict[str, Any]) -> dict[str, Any]:
    out = dict(result)
    out["quarters"] = [{**q, "lines": decorate_lines(q["lines"])} for q in result["quarters"]]
    return out


def levels() -> dict[str, Any]:
    return {"order": [lv.label for lv in sorted(Level, reverse=True)],
            "levels": [{"label": lv.label, "mark": lv.mark, "rank": int(lv), "uncalibrated": lv in UNCALIBRATED,
                        "meaning": LEVEL_MEANING[lv]} for lv in sorted(Level, reverse=True)],
            "metrics": [{"metric": name, "level": info.level.label, "formula": info.formula, "evidence": info.evidence,
                         "note": info.note, "inputs": list(info.inputs)} for name, info in METRICS.items()]}


def modules_catalog() -> dict[str, Any]:
    """The modeling ledger (structure and maturity only, no values) plus which modules can be decided now."""
    from marketplace_sim.business import catalog

    return {**catalog(), "is_private": False, "provenance": "public ledger (structure and maturity only)"}


def explain(metric: str) -> dict[str, Any]:
    info = lookup(metric)
    if info is None:
        raise ApiError(f"unknown metric '{metric}'")
    return {"metric": info.name, "level": info.level.label,
            "chain": [{"metric": c.name, "level": c.level.label, "formula": c.formula} for c in chain(metric)]}


# --- session -------------------------------------------------------------------------------------------------------

@dataclass
class Session:
    pack_dir: Path = SYNTHETIC_PACK
    pack: ParamPack = field(default_factory=lambda: load_pack(SYNTHETIC_PACK))
    state: CompanyState | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    seed: int = 0
    save_path: Path | None = None
    last_sweep: dict[str, Any] | None = None
    competitors: list[CompetitorSpec] | None = None  # game mode opponents; None = the engine's default bots
    game_meta: dict[str, Any] | None = None  # game mode settings shown back to the UI (opponents, objective)
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def is_private(self) -> bool:
        return self.pack.provenance != "synthetic"

    @property
    def scenario_dir(self) -> Path:
        return PRIVATE_ROOT / "scenarios" if self.is_private else SYNTHETIC_SCENARIOS

    @property
    def sweep_dir(self) -> Path:
        return PRIVATE_ROOT / "scenarios" if self.is_private else SYNTHETIC_SWEEPS


def pack_info(session: Session) -> dict[str, Any]:
    demand = session.pack.demand.get("model", "literature")
    return {"name": session.pack.name, "provenance": session.pack.provenance, "is_private": session.is_private,
            "source": "private" if session.is_private else "synthetic", "demand_model": demand,
            "quarter": session.state.quarter if session.state else None}


def load_pack_into(session: Session, source: str, path: str | None = None) -> dict[str, Any]:
    if source == "synthetic":
        directory = Path(path) if path else SYNTHETIC_PACK
        pack = load_pack(directory)
        if pack.provenance != "synthetic":
            raise ApiError("source 'synthetic' requires a pack whose provenance is synthetic")
    elif source == "private":
        directory = Path(path) if path else PRIVATE_ROOT / "model"
        if not _is_private_path(directory):
            raise ApiError("a private pack must live under a directory named 'private'")
        pack = load_pack(directory)
    else:
        raise ApiError("source must be 'synthetic' or 'private'")
    session.pack_dir, session.pack = directory.resolve(), pack
    session.state, session.history, session.save_path, session.last_sweep = None, [], None, None
    session.competitors, session.game_meta = None, None
    return pack_info(session)


# --- game (mpsim new / play / compare) --------------------------------------------------------------------------

def _state_dict(session: Session) -> dict[str, Any] | None:
    if session.state is None:
        return None
    data = session.state.to_dict()
    data["cash"] = {"value": session.state.cash, "level": session.state.cash_level,
                    "uncalibrated": Level[session.state.cash_level.upper()] in UNCALIBRATED}
    return data


def game(session: Session) -> dict[str, Any]:
    return {**pack_info(session), "state": _state_dict(session), "history": session.history}


def new_game(session: Session, quarter: int = 1) -> dict[str, Any]:
    session.state, session.history, session.save_path = CompanyState.initial(session.pack, quarter), [], None
    session.competitors, session.game_meta = None, None
    return game(session)


def load_save(session: Session, path: str) -> dict[str, Any]:
    """Open an mpsim save (schema marketplace-sim/save@1); its pack becomes the session pack."""
    save_path = Path(path)
    save = json.loads(save_path.read_text(encoding="utf-8"))
    if save.get("schema") != "marketplace-sim/save@1":
        raise ApiError("not an mpsim save")
    params = Path(save["params"])
    if not params.is_absolute():
        params = (save_path.parent / params).resolve()
    pack = load_pack(params)
    if pack.provenance != "synthetic" and not _is_private_path(save_path):
        raise ApiError("a save that uses a private pack must live under a directory named 'private'")
    session.pack_dir, session.pack = params, pack
    session.state = CompanyState.from_dict(save["state"])
    session.history = [{**h, "lines": decorate_lines(h["lines"])} for h in save.get("history", [])]
    session.save_path = save_path.resolve()
    return game(session)


def save_game(session: Session) -> dict[str, Any]:
    """Write the session back to the save it was loaded from (private saves only under a 'private' directory)."""
    if session.state is None or session.save_path is None:
        raise ApiError("no save loaded")
    if session.is_private and not _is_private_path(session.save_path):
        raise ApiError("refusing to write private results outside a directory named 'private'")
    save = json.loads(session.save_path.read_text(encoding="utf-8"))
    save["state"] = session.state.to_dict()
    save["history"] = [{"quarter": h["quarter"], "plan": h["plan"], "notes": h["notes"],
                        "lines": {k: {x: v[x] for x in ("value", "level", "source")} for k, v in h["lines"].items()}}
                       for h in session.history]
    session.save_path.write_text(json.dumps(save, indent=1), encoding="utf-8")
    return {"saved": True, "is_private": session.is_private}


def _require_state(session: Session) -> CompanyState:
    if session.state is None:
        session.state = CompanyState.initial(session.pack)
    return session.state


def session_competitors(session: Session) -> list[m.Competitor] | None:
    """Game-mode opponents built by the control plane (same code path as scenarios); None keeps the defaults."""
    if not session.competitors:
        return None
    scenario = ScenarioSpec(name="game-mode", base_params=str(session.pack_dir))
    return [build_competitor(spec, scenario) for spec in session.competitors]


def play(session: Session, plan: dict[str, Any]) -> dict[str, Any]:
    state = _require_state(session)
    new_state, report = advance(state, Plan.from_dict(plan, name=str(plan.get("name", "plan"))), session.pack,
                                competitors=session_competitors(session), seed=session.seed)
    session.state = new_state
    data = report_dict(report)
    session.history.append(data)
    return {**pack_info(session), "report": data, "state": _state_dict(session)}


def preview(session: Session, plan: dict[str, Any]) -> dict[str, Any]:
    state = _require_state(session)
    _, report = advance(state, Plan.from_dict(plan, name=str(plan.get("name", "plan"))), session.pack,
                        competitors=session_competitors(session), seed=session.seed)
    return {**pack_info(session), "report": report_dict(report)}


def compare(session: Session, plans: list[dict[str, Any]]) -> dict[str, Any]:
    state = _require_state(session)
    rivals = session_competitors(session)
    reports = [report_dict(advance(state, Plan.from_dict(p, name=str(p.get("name", f"plan-{i + 1}"))), session.pack,
                                   competitors=rivals, seed=session.seed)[1]) for i, p in enumerate(plans)]
    return {**pack_info(session), "quarter": state.quarter, "reports": reports}


def plan_presets(session: Session) -> dict[str, Any]:
    """Plan files offered in the decision editor (synthetic demo plans, or private plans for a private pack)."""
    directory = PRIVATE_ROOT / "plans" if session.is_private else SYNTHETIC_PLANS / "plans"
    presets = []
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        presets.append({"id": path.stem, "plan": {"name": data.get("name", path.stem), **data}})
    return {**pack_info(session), "presets": presets, "brand_types": [b.code for b in session.pack.brand_types],
            "stores": [s.key for s in session.pack.stores], "web_centers": [w.key for w in session.pack.web_centers],
            "capacity_options": [o.units for o in session.pack.capacity_options]}


# --- scenarios, events, sweeps, diff (control plane) ---------------------------------------------------------------

def scenario_templates(session: Session) -> dict[str, Any]:
    items = []
    for path in sorted(session.scenario_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if "base_params" in data:
            items.append({"id": path.stem, "spec": data})
    return {**pack_info(session), "templates": items}


def event_types() -> dict[str, Any]:
    return {"types": [{"type": t, **ev.EVENT_INFO[t]} for t in ev.EVENT_TYPES]}


def run_scenario(session: Session, spec: dict[str, Any]) -> dict[str, Any]:
    scenario = spec_from_dict(spec, str(session.scenario_dir))
    for event in scenario.events:
        ev.validate(event)
    pack = load_pack(scenario.resolve(scenario.base_params))
    result = decorate_result(_run_scenario(scenario).to_dict())
    return {"is_private": pack.provenance != "synthetic", "pack": pack.name, "result": result}


def sweep_files(session: Session) -> dict[str, Any]:
    items = []
    for path in sorted(session.sweep_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if "variables" in data and "base_scenario" in data:
            items.append({"id": path.stem, "sweep": data})
    return {**pack_info(session), "sweeps": items}


def run_sweep(session: Session, sweep: dict[str, Any]) -> dict[str, Any]:
    spec = sweep_from_dict(sweep, session.sweep_dir, str(sweep.get("name", "sweep")))
    result = _run_sweep(spec)
    base = spec_from_dict(yaml.safe_load(spec.base_scenario.read_text(encoding="utf-8")), str(spec.base_scenario.parent))
    is_private = load_pack(base.resolve(base.base_params)).provenance != "synthetic"
    session.last_sweep = {**result, "is_private": is_private}
    return session.last_sweep


def sweep_worst(session: Session, top: int = 10) -> dict[str, Any]:
    if session.last_sweep is None:
        raise ApiError("no sweep has been run in this session")
    return {"is_private": session.last_sweep["is_private"], "objective": session.last_sweep["objective"],
            "caveat": session.last_sweep["caveat"], "worst": _worst(session.last_sweep["rows"], top),
            "sensitivity": session.last_sweep["sensitivity"]}


def pack_snapshots(session: Session) -> dict[str, Any]:
    """Packs the diff screen can compare: synthetic examples, or the private quarterly snapshots."""
    if session.is_private:
        history = PRIVATE_ROOT / "model" / "history"
        items = [{"id": p.name, "path": str(p)} for p in sorted(history.iterdir()) if (p / "pack.json").exists()] \
            if history.exists() else []
        items.append({"id": "current", "path": str(PRIVATE_ROOT / "model")})
    else:
        items = [{"id": "synthetic", "path": str(SYNTHETIC_PACK)},
                 {"id": "synthetic-v2", "path": str(ROOT / "examples" / "demo-control" / "pack-v2")}]
    return {**pack_info(session), "packs": items}


def params_diff(old: str, new: str) -> dict[str, Any]:
    old_pack, new_pack = load_pack(Path(old)), load_pack(Path(new))
    synthetic = old_pack.provenance == "synthetic" and new_pack.provenance == "synthetic"
    changes = diff_dirs(Path(old), Path(new))
    rows = [{"path": c.path, "kind": c.kind, "module": c.module, "module_level": c.module_level.label,
             "relative": c.relative, "needs_reverification": c.needs_reverification,
             **({"old": c.old, "new": c.new} if synthetic else {})} for c in changes]
    return {"is_private": not synthetic, "values_included": synthetic, "old": old_pack.name, "new": new_pack.name,
            "red_flags": red_flags(changes), "changes": rows}
