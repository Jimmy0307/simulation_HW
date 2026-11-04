"""Business-module abstraction: one unit per business function, with an explicit maturity.

A business module takes its own decisions (``plan.modules[key]``) plus the pack and the carried state, and returns
tagged numbers. It never reaches into the engine: it hands back *effects* on a small, fixed set of coupling points,
and the engine applies them. Upgrading a module (heuristic -> literature -> verified) means registering a new
implementation for the same key with the same coupling points; the framework and the engine stay unchanged.

Coupling points (the only ways a module can change the quarter):

* demand    ``media_split[brand]``   split of a brand's goodwill across media (share, elasticity weight per medium);
                                     the demand chain's own advertising response is applied per medium (MCI form).
            ``selling_effort``       multiplier on the attraction of our offers (every market an offer reaches).
* production ``material_cost_factor`` multiplier on the component (material) part of every brand's unit cost.
* supply    ``inventory_release[brand]`` units taken out of carried inventory at quarter start (e.g. a sell-off).
            ``holding_rate``         expense = rate x value (units x unit cost) of inventory left at quarter end.
* cash      ``expenses``             expense lines charged this quarter (enter operating expenses and cash).
            ``income``               income lines this quarter (e.g. sell-off proceeds; enter pretax and cash).
            ``revenue_rates``        expense = rate x revenue (computed by the engine after demand, e.g. commission).
* state     ``state``                the module's own state, carried to the next quarter in ``module_state``.
* report    ``lines``                report-only lines (headcount, retention, mix index ...).

Every effect carries its own level. Demand couplings set the level of every number downstream of demand (units,
shares, revenue, profit, cash); production couplings set the level of unit and production cost; cash lines carry
their own level into profit and cash. "Downstream takes the weakest level" holds at every step.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged


class Maturity(StrEnum):
    """How far a business module is from the real game. Shown on every screen and document."""

    VERIFIED = "verified"  # captured from the game and reproduced (or fitted and passed hold-out validation)
    LITERATURE = "literature"  # functional form from published literature; coefficients not calibrated
    HEURISTIC = "heuristic"  # practice rule from general business sense; no literature, no calibration
    NOT_MODELED = "not-modeled"  # the real game has it; this engine does not

    @property
    def rank(self) -> int:
        return {Maturity.VERIFIED: 3, Maturity.LITERATURE: 2, Maturity.HEURISTIC: 1, Maturity.NOT_MODELED: 0}[self]


# The level a module part's outputs carry, per maturity (not-modeled parts produce nothing).
LEVEL_OF: dict[Maturity, Level] = {
    Maturity.VERIFIED: Level.VERIFIED,
    Maturity.LITERATURE: Level.LITERATURE,
    Maturity.HEURISTIC: Level.HEURISTIC,
}


def maturity_of(level: Level) -> Maturity:
    """Module maturity of a line level. Placeholder accounting rules count as heuristic (no literature, unverified)."""
    if level >= Level.ESTIMATED:
        return Maturity.VERIFIED
    if level == Level.LITERATURE:
        return Maturity.LITERATURE
    return Maturity.HEURISTIC


@dataclass(frozen=True)
class ModuleSpec:
    """What the framework needs to know about one implementation.

    ``rows`` maps every ledger row this implementation covers to the maturity of that part: one implementation can
    hold a literature part and a heuristic part (each output line is tagged with the level of the part behind it).
    """

    key: str  # plan.modules key, e.g. "marketing.media_mix"
    title: str
    rows: Mapping[str, Maturity]
    decisions: tuple[str, ...]  # decision fields read from plan.modules[key]
    outputs: tuple[str, ...]  # report lines it can produce
    couplings: tuple[str, ...]  # coupling points it uses (see module docstring)
    evidence: str  # where its form comes from (document path)

    @property
    def maturity(self) -> Maturity:
        """The weakest part (what the module as a whole can promise)."""
        return min(self.rows.values(), key=lambda m: m.rank)


@dataclass(frozen=True)
class BrandInput:
    name: str
    advertising: float
    production: float
    price: float


@dataclass(frozen=True)
class ModuleInput:
    pack: ParamPack
    quarter: int
    decisions: Mapping[str, Any]  # plan.modules[key]
    state: Mapping[str, float]  # module_state[key] carried from the previous quarter (empty at the start)
    brands: Sequence[BrandInput]  # the plan's brands this quarter
    markets_reached: int  # markets our offers reach this quarter
    inventory: Mapping[str, float] = field(default_factory=dict)  # units carried in at quarter start, per brand


@dataclass(frozen=True)
class MediaSplit:
    """A brand's goodwill split across media: (medium, share of spend, elasticity weight); weights sum to 1."""

    parts: tuple[tuple[str, float, float], ...]
    level: Level
    source: str


@dataclass
class ModuleResult:
    lines: dict[str, Tagged] = field(default_factory=dict)
    expenses: dict[str, Tagged] = field(default_factory=dict)
    income: dict[str, Tagged] = field(default_factory=dict)
    revenue_rates: dict[str, Tagged] = field(default_factory=dict)
    media_split: dict[str, MediaSplit] = field(default_factory=dict)
    selling_effort: Tagged | None = None
    material_cost_factor: Tagged | None = None
    inventory_release: dict[str, Tagged] = field(default_factory=dict)
    holding_rate: Tagged | None = None
    salvage_fraction: Tagged | None = None  # value of released units as a fraction of unit cost (income)
    state: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


class BusinessModule(Protocol):
    spec: ModuleSpec

    def run(self, inp: ModuleInput) -> ModuleResult:
        """One quarter of this module: decisions + carried state -> tagged effects and lines."""


class ModuleDecisionError(ValueError):
    """A decision a module refuses (bad value, or a module that is not modeled yet)."""


def number(decisions: Mapping[str, Any], key: str, default: float, *, low: float = 0.0,
           high: float | None = None) -> float:
    """Read one numeric decision with bounds; refuse values outside them instead of clamping silently."""
    raw = decisions.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ModuleDecisionError(f"{key} must be a number") from exc
    if math.isnan(value) or value < low or (high is not None and value > high):
        bound = f"between {low:g} and {high:g}" if high is not None else f">= {low:g}"
        raise ModuleDecisionError(f"{key} must be {bound}")
    return value


def in_range(name: str, value: float, low: float, high: float) -> float:
    """A coefficient that must stay inside its published range (literature parts)."""
    if not low <= value <= high:
        raise ValueError(f"{name}={value:g} is outside its literature range [{low:g}, {high:g}]")
    return value
