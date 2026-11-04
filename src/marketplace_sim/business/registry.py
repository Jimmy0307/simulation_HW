"""Business-module registry: which implementation runs for each plan.modules key, and the ledger behind it.

``data/modeling_ledger.json`` lists every business function of a full company simulation with its maturity
(docs/modeling-ledger.md is rendered from it). ``IMPLEMENTATIONS`` maps the keys that have an implementation to its
class. Upgrading a module = replace the class for its key (same coupling points) and update the ledger row; the
consistency test (tests/test_business_modules.py) fails if the two disagree.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from marketplace_sim.business.base import (
    LEVEL_OF,
    BusinessModule,
    Maturity,
    ModuleDecisionError,
    ModuleInput,
    ModuleResult,
)
from marketplace_sim.business.marketing import MediaMixHeuristic
from marketplace_sim.business.sales_force import SalesForceHeuristic
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

DATA = Path(__file__).resolve().parents[3] / "data"
LEDGER_FILE = DATA / "modeling_ledger.json"
DEFAULTS_FILE = DATA / "module_defaults.json"
LEDGER_SCHEMA = "marketplace-sim/modeling-ledger@1"
DEFAULTS_SCHEMA = "marketplace-sim/module-defaults@1"

IMPLEMENTATIONS: dict[str, type[Any]] = {
    MediaMixHeuristic.spec.key: MediaMixHeuristic,
    SalesForceHeuristic.spec.key: SalesForceHeuristic,
}


def ledger() -> dict[str, Any]:
    path = Path(os.environ.get("MPSIM_MODELING_LEDGER", str(LEDGER_FILE)))
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != LEDGER_SCHEMA:
        raise ValueError(f"{path} is not a {LEDGER_SCHEMA} file")
    return data


def ledger_rows() -> list[dict[str, Any]]:
    return list(ledger()["modules"])


def defaults() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DEFAULTS_FILE.read_text(encoding="utf-8"))
    if data.get("schema") != DEFAULTS_SCHEMA:
        raise ValueError(f"{DEFAULTS_FILE} is not a {DEFAULTS_SCHEMA} file")
    return dict(data["modules"])


def coefficients(pack: ParamPack, key: str) -> dict[str, Any]:
    """Labelled defaults <- pack ``modules.<key>`` overrides. Unknown keys are refused."""
    base = dict(defaults().get(key, {}).get("coefficients", {}))
    override = dict(pack.modules.get(key) or {})
    unknown = set(override) - set(base)
    if unknown:
        raise ValueError(f"unknown coefficient(s) for module {key}: {', '.join(sorted(unknown))}")
    return {**base, **override}


def build(pack: ParamPack, key: str) -> BusinessModule:
    module: BusinessModule = IMPLEMENTATIONS[key](coefficients(pack, key))
    return module


@dataclass
class ModuleEffects:
    """All active modules of one quarter, merged. ``level`` is None when no module is active."""

    level: Level | None = None
    active: list[str] = field(default_factory=list)
    lines: dict[str, Tagged] = field(default_factory=dict)
    expenses: dict[str, Tagged] = field(default_factory=dict)
    revenue_rates: dict[str, Tagged] = field(default_factory=dict)
    ad_efficiency: dict[str, Tagged] = field(default_factory=dict)
    selling_effort: Tagged | None = None
    state: dict[str, dict[str, float]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def ledger_rows_for(module_key: str) -> list[dict[str, Any]]:
    """Ledger rows implemented by one plan.modules key (one implementation can cover several rows)."""
    return [r for r in ledger_rows() if r.get("module") == module_key]


def _refusal(key: str) -> str:
    row = next((r for r in ledger_rows() if r["key"] == key), None)
    if row is None:
        known = ", ".join(sorted(IMPLEMENTATIONS))
        return f"unknown business module '{key}' (modules with an implementation: {known})"
    if row.get("module") in IMPLEMENTATIONS:
        return f"'{key}' is decided under plan.modules['{row['module']}']"
    return (f"module '{key}' ({row['name']}) is {row['maturity']}: it has no implementation yet, so it cannot be "
            f"decided. Next step: {row['next_step']}")


def run_modules(pack: ParamPack, *, quarter: int, decisions: Mapping[str, Any],
                carried: Mapping[str, Mapping[str, float]], brands: Sequence[tuple[str, float]],
                markets_reached: int) -> ModuleEffects:
    """Run every module the plan decides on (``plan.modules``) or that carries state (a sales force stays employed),
    in key order, and merge their effects."""
    effects = ModuleEffects()
    for key in sorted(set(decisions) | {k for k, v in carried.items() if v}):
        if key not in IMPLEMENTATIONS:
            raise ModuleDecisionError(_refusal(key))
        block = decisions.get(key, {})
        if not isinstance(block, Mapping):
            raise ModuleDecisionError(f"plan.modules['{key}'] must be a mapping of decisions")
        module = build(pack, key)
        result: ModuleResult = module.run(ModuleInput(pack, quarter, block, dict(carried.get(key, {})), brands,
                                                      markets_reached))
        level = LEVEL_OF[module.spec.maturity]
        effects.level = level if effects.level is None else min(effects.level, level)
        effects.active.append(key)
        effects.lines.update(result.lines)
        effects.expenses.update(result.expenses)
        effects.revenue_rates.update(result.revenue_rates)
        for brand, eff in result.ad_efficiency.items():
            prior = effects.ad_efficiency.get(brand)
            effects.ad_efficiency[brand] = eff if prior is None else Tagged(
                prior.value * eff.value, min(prior.level, eff.level), f"({prior.source}) x ({eff.source})")
        if result.selling_effort is not None:
            prior_effort = effects.selling_effort
            effects.selling_effort = result.selling_effort if prior_effort is None else Tagged(
                prior_effort.value * result.selling_effort.value, min(prior_effort.level, result.selling_effort.level),
                f"({prior_effort.source}) x ({result.selling_effort.source})")
        if result.state:
            effects.state[key] = dict(result.state)
        effects.notes.extend(f"{key}: {n}" if not n.startswith(key) else n for n in result.notes)
    return effects


def catalog() -> dict[str, Any]:
    """The ledger plus, per row, whether it can be decided now and the implementation behind it (API / UI)."""
    data = ledger()
    base_defaults = defaults()
    rows = []
    for row in data["modules"]:
        impl = IMPLEMENTATIONS.get(row.get("module", ""))
        rows.append({**row, "module": row.get("module"), "decidable": impl is not None,
                     "implementation": impl.__name__ if impl else None,
                     "decisions": list(impl.spec.decisions) if impl else [],
                     "coefficients": base_defaults.get(row["module"], {}).get("coefficients") if impl else None})
    counts: dict[str, int] = {m.value: 0 for m in Maturity}
    for row in rows:
        counts[row["maturity"]] += 1
    return {**{k: v for k, v in data.items() if k != "modules"}, "modules": rows, "counts": counts}
