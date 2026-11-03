"""Source levels attached to every number the engine produces.

A computed value is only as trustworthy as its weakest input, so combining tagged values keeps the lowest level.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum


class Level(IntEnum):
    """Higher is stronger. Ordering is used to take the weakest level of a combination."""

    PLACEHOLDER = 0  # illustrative, uncalibrated
    LITERATURE = 1  # functional form backed by published literature; coefficients not calibrated on this game
    ESTIMATED = 2  # fitted to observed data (e.g. a demand model)
    DERIVED = 3  # follows directly from published parameters; not separately measured
    VERIFIED = 4  # reproduced against measured server results with zero residual

    @property
    def mark(self) -> str:
        return {Level.VERIFIED: "V", Level.DERIVED: "D", Level.ESTIMATED: "E", Level.LITERATURE: "L",
                Level.PLACEHOLDER: "P"}[self]

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Tagged:
    """A number with its source level and the rule that produced it."""

    value: float
    level: Level
    source: str

    def __add__(self, other: Tagged) -> Tagged:
        return Tagged(self.value + other.value, min(self.level, other.level), f"({self.source}) + ({other.source})")

    def __sub__(self, other: Tagged) -> Tagged:
        return Tagged(self.value - other.value, min(self.level, other.level), f"({self.source}) - ({other.source})")

    def scaled(self, factor: float, why: str) -> Tagged:
        return Tagged(self.value * factor, self.level, f"{self.source} x {why}")

    def with_level(self, level: Level, source: str | None = None) -> Tagged:
        return Tagged(self.value, min(self.level, level), source or self.source)

    def render(self) -> str:
        return f"{self.value:,.2f} [{self.level.mark}]"


def total(items: Iterable[Tagged], source: str, *, empty_level: Level = Level.VERIFIED) -> Tagged:
    values = list(items)
    if not values:
        return Tagged(0.0, empty_level, source)
    return Tagged(sum(v.value for v in values), min(v.level for v in values), source)


def const(value: float, level: Level, source: str) -> Tagged:
    return Tagged(float(value), level, source)
