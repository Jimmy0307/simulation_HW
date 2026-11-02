"""Finite-difference analysis over recorded observations only."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class SensitivityResult:
    variable: str
    metric: str
    baseline_value: float
    minus_value: float | None
    plus_value: float | None
    central_difference: float | None
    forward_difference: float | None
    backward_difference: float | None
    provenance: str = "SURROGATE_MODEL"


def finite_difference(
    variable: str,
    metric: str,
    baseline: tuple[float, float],
    observations: Iterable[tuple[float, float]],
) -> SensitivityResult:
    x0, y0 = baseline
    values = {x: y for x, y in observations}
    lower = max((x for x in values if x < x0), default=None)
    upper = min((x for x in values if x > x0), default=None)
    backward = (y0 - values[lower]) / (x0 - lower) if lower is not None else None
    forward = (values[upper] - y0) / (upper - x0) if upper is not None else None
    central = (values[upper] - values[lower]) / (upper - lower) if lower is not None and upper is not None else None
    return SensitivityResult(
        variable=variable,
        metric=metric,
        baseline_value=y0,
        minus_value=values.get(lower) if lower is not None else None,
        plus_value=values.get(upper) if upper is not None else None,
        central_difference=central,
        forward_difference=forward,
        backward_difference=backward,
    )
