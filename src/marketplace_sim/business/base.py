"""Business-module abstraction: one unit per business function, with an explicit maturity.

A business module takes its own decisions (``plan.modules[key]``) plus the pack and the carried state, and returns
tagged numbers. It never reaches into the engine: it hands back *effects* on a small, fixed set of coupling points,
and the engine applies them. Upgrading a module (heuristic -> literature -> verified) means registering a new
implementation for the same key with the same coupling points; the framework and the engine stay unchanged.

Coupling points (the only ways a module can change the quarter):

* ``ad_efficiency[brand]``  multiplier on the advertising that enters the demand chain (goodwill input).
* ``selling_effort``        multiplier on the attraction of our offers (every market an offer reaches).
* ``expenses``              expense lines charged this quarter (enter operating expenses and cash).
* ``revenue_rates``         expense = rate x revenue (computed by the engine after demand, e.g. commission).
* ``state``                 the module's own state, carried to the next quarter in ``CompanyState.module_state``.
* ``lines``                 report-only lines (headcount, retention, efficiency ...).

Every effect carries a level. The engine takes the weakest level of all active modules and applies it to every
number downstream of a demand coupling point (units, shares, revenue, profit, cash): a heuristic input makes the
whole chain heuristic.
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


# The level a module's outputs carry, per maturity (not-modeled modules produce nothing).
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
    """What the framework needs to know about one implementation."""

    key: str  # plan.modules key, e.g. "marketing.media_mix"
    title: str
    maturity: Maturity
    decisions: tuple[str, ...]  # decision fields read from plan.modules[key]
    outputs: tuple[str, ...]  # report lines it can produce
    couplings: tuple[str, ...]  # coupling points it uses (see module docstring)
    evidence: str  # where its form comes from (document path)


@dataclass(frozen=True)
class ModuleInput:
    pack: ParamPack
    quarter: int
    decisions: Mapping[str, Any]  # plan.modules[key]
    state: Mapping[str, float]  # module_state[key] carried from the previous quarter (empty at the start)
    brands: Sequence[tuple[str, float]]  # (brand name, advertising this quarter) from the plan
    markets_reached: int  # markets our offers reach this quarter


@dataclass
class ModuleResult:
    lines: dict[str, Tagged] = field(default_factory=dict)
    expenses: dict[str, Tagged] = field(default_factory=dict)
    revenue_rates: dict[str, Tagged] = field(default_factory=dict)
    ad_efficiency: dict[str, Tagged] = field(default_factory=dict)
    selling_effort: Tagged | None = None
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
