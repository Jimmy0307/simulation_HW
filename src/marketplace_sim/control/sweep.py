"""Batch stress testing: expand a sweep definition into ScenarioSpecs, run them, rank the worst, measure sensitivity.

Sweep YAML::

  name: stress
  base_scenario: baseline.yaml          # relative to the sweep file
  mode: grid | sample                   # sample draws `samples` combinations with `seed`
  samples: 20
  seed: 7
  objective: final_cash                 # final_cash | min_cash | cumulative_net_income
  variables:
    - {name: capacity_cost, path: "capacity_options[*].cost", op: scale, values: [0.9, 1.0, 1.15], base: 1.0}
    - {name: demand_q2, event: {type: demand_shock, from_quarter: 2, target: "*"}, values: [-0.3, 0.0, 0.1], base: 0.0}
    - {name: rivals, competitors: {calm: [{name: a, strategy: baseline}], wild: [{name: b, strategy: random}]}}
    - {name: seed, seeds: [0, 1, 2]}
    - {name: plan, policies: {cautious: {type: fixed, default: plans/a.yaml}, bold: {type: fixed, default: plans/c.yaml}}}

Policy file references inside ``policies`` are relative to the sweep file.
"""

from __future__ import annotations

import copy
import itertools
import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from marketplace_sim.control.runner import run_scenario
from marketplace_sim.control.spec import (
    CompetitorSpec,
    EventSpec,
    Override,
    ScenarioSpec,
    load_spec,
)
from marketplace_sim.provenance import Level
from marketplace_sysid.experiments.sensitivity import finite_difference

SWEEP_SCHEMA = "marketplace-sim/sweep-result@1"
OBJECTIVES = ("final_cash", "min_cash", "cumulative_net_income")


@dataclass
class Variable:
    name: str
    kind: str  # override | event | competitors | seed | policy
    values: list[Any]
    base: Any = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SweepSpec:
    name: str
    base_scenario: Path
    variables: list[Variable]
    mode: str = "grid"
    samples: int = 20
    seed: int = 0
    objective: str = "final_cash"


def _rebase_policy(policy: dict[str, Any], sweep_dir: Path, scenario_dir: Path) -> dict[str, Any]:
    """Re-express policy file references (written relative to the sweep file) relative to the base scenario.

    Relative paths keep scenario fingerprints independent of where the repository is checked out.
    """

    def rebase(ref: Any) -> str:
        return Path(os.path.relpath((sweep_dir / str(ref)).resolve(), scenario_dir)).as_posix()

    out = dict(policy)
    for key in ("default", "dir"):
        if key in out:
            out[key] = rebase(out[key])
    if out.get("plans"):
        out["plans"] = {k: rebase(v) for k, v in dict(out["plans"]).items()}
    return out


def load_sweep(path: Path) -> SweepSpec:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    variables = []
    for raw in data.get("variables") or []:
        name = str(raw["name"])
        if "path" in raw:
            variables.append(Variable(name, "override", list(raw["values"]), raw.get("base"),
                                      {"path": raw["path"], "op": raw.get("op", "scale")}))
        elif "event" in raw:
            variables.append(Variable(name, "event", list(raw["values"]), raw.get("base"), dict(raw["event"])))
        elif "competitors" in raw:
            options = dict(raw["competitors"])
            variables.append(Variable(name, "competitors", list(options), raw.get("base"), options))
        elif "policies" in raw:
            scenario_dir = (path.parent / data["base_scenario"]).resolve().parent
            options = {str(k): _rebase_policy(dict(v), path.parent.resolve(), scenario_dir)
                       for k, v in dict(raw["policies"]).items()}
            variables.append(Variable(name, "policy", list(options), raw.get("base"), options))
        elif "seeds" in raw:
            variables.append(Variable(name, "seed", list(raw["seeds"]), raw.get("base")))
        else:
            raise ValueError(f"variable '{name}' needs path, event, competitors, policies or seeds")
    objective = str(data.get("objective", "final_cash"))
    if objective not in OBJECTIVES:
        raise ValueError(f"objective must be one of {OBJECTIVES}")
    return SweepSpec(str(data.get("name", path.stem)), (path.parent / data["base_scenario"]).resolve(), variables,
                     str(data.get("mode", "grid")), int(data.get("samples", 20)), int(data.get("seed", 0)), objective)


def expand(sweep: SweepSpec) -> list[tuple[dict[str, Any], ScenarioSpec]]:
    """Return (assignment, scenario) pairs. Deterministic for a given sweep definition."""
    base = load_spec(sweep.base_scenario)
    grids = [v.values for v in sweep.variables]
    if sweep.mode == "grid":
        combos = list(itertools.product(*grids))
    elif sweep.mode == "sample":
        rng = random.Random(sweep.seed)
        seen: list[tuple[Any, ...]] = []
        total = 1
        for values in grids:
            total *= len(values)
        while len(seen) < min(sweep.samples, total):
            combo = tuple(rng.choice(values) for values in grids)
            if combo not in seen:
                seen.append(combo)
        combos = seen
    else:
        raise ValueError("mode must be grid or sample")
    out = []
    for index, combo in enumerate(combos):
        spec = copy.deepcopy(base)
        spec.name = f"{sweep.name}-{index:03d}"
        assignment = {}
        for variable, value in zip(sweep.variables, combo, strict=True):
            assignment[variable.name] = value
            if variable.kind == "override":
                spec.overrides = [*spec.overrides, Override(variable.payload["path"], variable.payload["op"], value)]
            elif variable.kind == "event":
                e = variable.payload
                spec.events = [*spec.events, EventSpec(str(e["type"]), int(e.get("from_quarter", e.get("quarter", 1))), float(value),
                                                       str(e.get("target", "*")), int(e.get("duration", 1)),
                                                       f"{variable.name}={value}")]
            elif variable.kind == "competitors":
                spec.competitors = [CompetitorSpec(str(c["name"]), str(c.get("strategy", "baseline")),
                                                   dict(c.get("params") or {})) for c in variable.payload[value]]
            elif variable.kind == "policy":
                spec.our_policy = dict(variable.payload[value])
            elif variable.kind == "seed":
                spec.seed = int(value)
        out.append((assignment, spec))
    return out


def run_sweep(sweep: SweepSpec) -> dict[str, Any]:
    rows = []
    for assignment, spec in expand(sweep):
        result = run_scenario(spec)
        summary = result.summary()
        rows.append({"id": spec.name, "fingerprint": result.fingerprint, "assignment": assignment,
                     "objective": summary[sweep.objective], "summary": summary})
    level = demand_level(rows)
    return {"schema": SWEEP_SCHEMA, "name": sweep.name, "objective": sweep.objective, "mode": sweep.mode,
            "demand_level": level, "caveat": caveat(level),
            "rows": rows, "worst": worst(rows, 5), "sensitivity": sensitivity(sweep, rows)}


def demand_level(rows: list[dict[str, Any]]) -> str:
    """Weakest source level of revenue across all runs (revenue carries the demand model's level)."""
    levels = [Level[r["summary"]["weakest_level"]["revenue"].upper()] for r in rows
              if r["summary"]["weakest_level"].get("revenue")]
    return min(levels, default=Level.PLACEHOLDER).label


def caveat(level: str) -> str:
    if Level[level.upper()] >= Level.ESTIMATED:
        return ""
    return (f"Demand is at '{level}' level: the worst cases reflect {level} demand assumptions (published forms with "
            "uncalibrated coefficients, or placeholders), not a forecast of this game. Cost-side lines keep their "
            "own levels.")


def worst(rows: list[dict[str, Any]], top: int) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: (r["objective"] if r["objective"] is not None else float("inf"), r["id"]))[:top]


def sensitivity(sweep: SweepSpec, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Main effect per variable (range of mean objective across its values) and a local slope for numeric ones."""
    out = []
    for variable in sweep.variables:
        means: dict[Any, float] = {}
        for value in variable.values:
            hits = [r["objective"] for r in rows if r["assignment"].get(variable.name) == value and r["objective"] is not None]
            if hits:
                means[value] = sum(hits) / len(hits)
        entry: dict[str, Any] = {"variable": variable.name, "kind": variable.kind,
                                 "mean_objective_by_value": {str(k): v for k, v in means.items()},
                                 "main_effect_range": (max(means.values()) - min(means.values())) if means else None}
        numeric = [v for v in means if isinstance(v, (int, float)) and not isinstance(v, bool)]
        base = variable.base if variable.base in means else (sorted(numeric)[len(numeric) // 2] if numeric else None)
        if variable.kind in {"override", "event"} and base is not None and len(numeric) >= 2:
            fd = finite_difference(variable.name, sweep.objective, (float(base), means[base]),
                                   [(float(v), means[v]) for v in numeric if v != base])
            entry["local_slope"] = fd.central_difference if fd.central_difference is not None else (
                fd.forward_difference if fd.forward_difference is not None else fd.backward_difference)
        out.append(entry)
    return sorted(out, key=lambda e: -(e["main_effect_range"] or 0))


def write_sweep(result: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result['name']}.sweep.json"
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    lines = [f"# Sweep {result['name']} (objective: {result['objective']})", "",
             *([f"> {result['caveat']}", ""] if result.get("caveat") else []),
             "| id | objective | " + " | ".join(result["rows"][0]["assignment"]) + " | fingerprint |",
             "|---|---|" + "---|" * len(result["rows"][0]["assignment"]) + "---|"] if result["rows"] else []
    for row in result["rows"]:
        objective = "-" if row["objective"] is None else f"{row['objective']:,.0f}"
        lines.append(f"| {row['id']} | {objective} | " + " | ".join(str(v) for v in row["assignment"].values())
                     + f" | {row['fingerprint']} |")
    (out_dir / f"{result['name']}.sweep.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
