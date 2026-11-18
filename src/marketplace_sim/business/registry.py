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

from marketplace_sim.business.accounting import AccrualAccounting
from marketplace_sim.business.base import (
    BrandInput,
    BusinessModule,
    Maturity,
    MediaSplit,
    Metric,
    ModuleDecisionError,
    ModuleInput,
    ModuleResult,
    Outcome,
)
from marketplace_sim.business.finance import FinancingModule
from marketplace_sim.business.inventory import InventoryModule
from marketplace_sim.business.marketing import MediaMixLiterature
from marketplace_sim.business.marketing_more import (
    AdCopyModule,
    InternetMarketingModule,
    PromotionsModule,
)
from marketplace_sim.business.operations import (
    CultureModule,
    ExcessCapacityModule,
    FactoryLocationModule,
    OperatingCapacityModule,
    ProductionWorkersModule,
)
from marketplace_sim.business.planning import ProductionPlanningModule
from marketplace_sim.business.product import LearningCurveModule, QualityModule, RnDModule
from marketplace_sim.business.purchasing import PurchasingHeuristic
from marketplace_sim.business.research import MarketResearchModule, ScorecardModule
from marketplace_sim.business.sales_force import SalesForceModule
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

DATA = Path(__file__).resolve().parents[3] / "data"
LEDGER_FILE = DATA / "modeling_ledger.json"
DEFAULTS_FILE = DATA / "module_defaults.json"
LEDGER_SCHEMA = "marketplace-sim/modeling-ledger@1"
DEFAULTS_SCHEMA = "marketplace-sim/module-defaults@1"

IMPLEMENTATIONS: dict[str, type[Any]] = {cls.spec.key: cls for cls in (
    MediaMixLiterature, SalesForceModule, InventoryModule, PurchasingHeuristic,
    PromotionsModule, AdCopyModule, InternetMarketingModule, MarketResearchModule,
    ProductionWorkersModule, CultureModule, OperatingCapacityModule, FactoryLocationModule, ExcessCapacityModule,
    ProductionPlanningModule, QualityModule, RnDModule, LearningCurveModule,
    FinancingModule, AccrualAccounting, ScorecardModule,
)}


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


def module_metrics() -> list[Metric]:
    """Report lines declared by the module implementations (``metrics`` class attribute)."""
    return [m for cls in IMPLEMENTATIONS.values() for m in getattr(cls, "metrics", ())]


def build(pack: ParamPack, key: str) -> BusinessModule:
    module: BusinessModule = IMPLEMENTATIONS[key](coefficients(pack, key), pack)
    return module


def _times(a: Tagged | None, b: Tagged) -> Tagged:
    return b if a is None else Tagged(a.value * b.value, min(a.level, b.level), f"({a.source}) x ({b.source})")


def _plus(a: Tagged | None, b: Tagged) -> Tagged:
    return b if a is None else a + b


@dataclass
class ModuleEffects:
    """All active modules of one quarter, merged. A level is None when no effect touches that family."""

    active: list[str] = field(default_factory=list)
    demand_level: Level | None = None  # weakest level of the demand couplings actually used
    lines: dict[str, Tagged] = field(default_factory=dict)
    expenses: dict[str, Tagged] = field(default_factory=dict)
    income: dict[str, Tagged] = field(default_factory=dict)
    revenue_rates: dict[str, Tagged] = field(default_factory=dict)
    media_split: dict[str, MediaSplit] = field(default_factory=dict)
    selling_effort: Tagged | None = None
    material_cost_factor: Tagged | None = None
    inventory_release: dict[str, Tagged] = field(default_factory=dict)
    holding_rate: Tagged | None = None
    salvage_fraction: Tagged | None = None
    attraction: dict[str, Tagged] = field(default_factory=dict)
    price_factor: dict[str, Tagged] = field(default_factory=dict)
    capacity_factor: Tagged | None = None
    capacity_extra: Tagged | None = None
    labor_cost_factor: Tagged | None = None
    conversion_factor: dict[str, Tagged] = field(default_factory=dict)
    unit_cost_add: dict[str, Tagged] = field(default_factory=dict)
    production_units: dict[str, Tagged] = field(default_factory=dict)
    production_order: tuple[str, ...] | None = None
    financing: dict[str, Tagged] = field(default_factory=dict)
    state: dict[str, dict[str, float]] = field(default_factory=dict)
    stopped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    modules: dict[str, tuple[Any, ModuleInput]] = field(default_factory=dict)

    def _demand(self, level: Level) -> None:
        self.demand_level = level if self.demand_level is None else min(self.demand_level, level)

    @property
    def capacity_level(self) -> Level | None:
        levels = [t.level for t in (self.capacity_factor, self.capacity_extra) if t is not None]
        return min(levels) if levels else None

    def hook(self, name: str, outcome: Outcome) -> list[tuple[str, Any]]:
        """Run one after-demand hook (settle, tax, close) of every active module that has it, in key order."""
        out = []
        for key, (module, inp) in self.modules.items():
            fn = getattr(module, name, None)
            if fn is not None:
                out.append((key, fn(inp, outcome)))
        return out

    def merge_late(self, key: str, result: ModuleResult) -> None:
        """Lines, expenses, income and state from a settle / close hook."""
        self.lines.update(result.lines)
        self.expenses.update(result.expenses)
        self.income.update(result.income)
        if result.state:
            self.state[key] = {**self.state.get(key, {}), **result.state}
        self.notes.extend(f"{key}: {n}" for n in result.notes)


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
                carried: Mapping[str, Mapping[str, float]], brands: Sequence[BrandInput],
                markets_reached: int, inventory: Mapping[str, float] | None = None, web_share: float = 0.0,
                capacity_units: float = 0.0) -> ModuleEffects:
    """Run every module the plan decides on (``plan.modules``) or that carries state (a sales force stays employed),
    in key order, and merge their effects."""
    effects = ModuleEffects()
    for key in sorted(set(decisions) | {k for k, v in carried.items() if v}):
        if key not in IMPLEMENTATIONS:
            raise ModuleDecisionError(_refusal(key))
        block = decisions.get(key, {})
        if not isinstance(block, Mapping):
            raise ModuleDecisionError(f"plan.modules['{key}'] must be a mapping of decisions")
        if block.get("stop") is True:  # a model option switched off: drop its state, no effect this quarter
            if not getattr(IMPLEMENTATIONS[key], "stoppable", False):
                raise ModuleDecisionError(f"'{key}' cannot be stopped (it carries obligations); decide it to zero")
            effects.stopped.append(key)
            continue
        block = {k: v for k, v in block.items() if k != "stop"}
        module = build(pack, key)
        inp = ModuleInput(pack, quarter, block, dict(carried.get(key, {})), brands, markets_reached,
                          dict(inventory or {}), web_share, capacity_units)
        result: ModuleResult = module.run(inp)
        effects.modules[key] = (module, inp)
        effects.active.append(key)
        effects.lines.update(result.lines)
        effects.expenses.update(result.expenses)
        effects.income.update(result.income)
        effects.revenue_rates.update(result.revenue_rates)
        for brand, split in result.media_split.items():
            if brand in effects.media_split:
                raise ModuleDecisionError(f"two modules split the advertising of {brand}")
            effects.media_split[brand] = split
            effects._demand(split.level)
        if result.selling_effort is not None:
            effects.selling_effort = _times(effects.selling_effort, result.selling_effort)
            effects._demand(result.selling_effort.level)
        if result.material_cost_factor is not None:
            effects.material_cost_factor = _times(effects.material_cost_factor, result.material_cost_factor)
        for brand, units in result.inventory_release.items():
            prior = effects.inventory_release.get(brand)
            effects.inventory_release[brand] = units if prior is None else prior + units
        if result.holding_rate is not None:
            prior_rate = effects.holding_rate
            effects.holding_rate = result.holding_rate if prior_rate is None else prior_rate + result.holding_rate
        if result.salvage_fraction is not None:
            effects.salvage_fraction = result.salvage_fraction
        _merge_round2(effects, key, result)
        if result.state:
            effects.state[key] = dict(result.state)
        effects.notes.extend(f"{key}: {n}" for n in result.notes)
    return effects


def _merge_round2(effects: ModuleEffects, key: str, result: ModuleResult) -> None:
    for brand, factor in result.attraction.items():
        effects.attraction[brand] = _times(effects.attraction.get(brand), factor)
        effects._demand(factor.level)
    for brand, factor in result.price_factor.items():
        effects.price_factor[brand] = _times(effects.price_factor.get(brand), factor)
        effects._demand(factor.level)
    if result.capacity_factor is not None:
        effects.capacity_factor = _times(effects.capacity_factor, result.capacity_factor)
    if result.capacity_extra is not None:
        effects.capacity_extra = _plus(effects.capacity_extra, result.capacity_extra)
    if result.labor_cost_factor is not None:
        effects.labor_cost_factor = _times(effects.labor_cost_factor, result.labor_cost_factor)
    for brand, factor in result.conversion_factor.items():
        effects.conversion_factor[brand] = _times(effects.conversion_factor.get(brand), factor)
    for brand, add in result.unit_cost_add.items():
        effects.unit_cost_add[brand] = _plus(effects.unit_cost_add.get(brand), add)
    for brand, units in result.production_units.items():
        if brand in effects.production_units:
            raise ModuleDecisionError(f"two modules set the production of {brand}")
        effects.production_units[brand] = units
    if result.production_order is not None:
        if effects.production_order is not None:
            raise ModuleDecisionError("two modules set the production order")
        effects.production_order = result.production_order
    for name, flow in result.financing.items():
        effects.financing[name] = flow


def catalog() -> dict[str, Any]:
    """The ledger plus, per row, whether it can be decided now and the implementation behind it (API / UI)."""
    data = ledger()
    base_defaults = defaults()
    rows = []
    for row in data["modules"]:
        impl = IMPLEMENTATIONS.get(row.get("module", ""))
        entry = base_defaults.get(row.get("module", ""), {}) if impl else {}
        rows.append({**row, "module": row.get("module"), "decidable": impl is not None,
                     "implementation": impl.__name__ if impl else None,
                     "decisions": list(impl.spec.decisions) if impl else [],
                     "coefficients": entry.get("coefficients") if impl else None,
                     "ranges": entry.get("ranges") if impl else None,
                     "primary": impl is not None and next(iter(impl.spec.rows)) == row["key"],
                     "fields": [f.to_dict() for f in getattr(impl, "fields", ())] if impl else [],
                     "ui": dict(getattr(impl, "ui", {})) if impl else None,
                     "stoppable": bool(getattr(impl, "stoppable", False)) if impl else False})
    counts: dict[str, int] = {m.value: 0 for m in Maturity}
    for row in rows:
        counts[row["maturity"]] += 1
    history = list(data.get("history", []))
    return {**{k: v for k, v in data.items() if k not in {"modules", "history"}}, "modules": rows, "counts": counts,
            "history": history}
