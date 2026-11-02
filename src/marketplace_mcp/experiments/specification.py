"""Dry-run experiment model with irreversible actions prohibited."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any

DRY_RUN = True
READ_ONLY = True
ALLOW_WRITE = False
ALLOW_FINAL_SUBMIT = False


@dataclass(frozen=True)
class DecisionVariable:
    name: str
    unit: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    evidence: list[str] = field(default_factory=list)
    provenance: str = "UNKNOWN"


@dataclass(frozen=True)
class BaselineState:
    values: dict[str, float]
    state_ref: str = "UNKNOWN"


@dataclass(frozen=True)
class Perturbation:
    variable: str
    offset: float
    label: str


@dataclass(frozen=True)
class ObservedOutput:
    metric: str
    value: float
    observation_ref: str


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    baseline: BaselineState
    variables: list[DecisionVariable]
    perturbations: list[Perturbation]
    metrics: list[str]
    hypotheses: list[str] = field(default_factory=list)
    design: str = "ONE_FACTOR_AT_A_TIME"
    dry_run: bool = DRY_RUN
    read_only: bool = READ_ONLY
    allow_write: bool = ALLOW_WRITE
    allow_final_submit: bool = ALLOW_FINAL_SUBMIT
    status: str = "PROPOSED_NOT_EXECUTED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def propose_one_factor_experiment(
    variable: DecisionVariable,
    metric: str,
    baseline: BaselineState,
    *,
    delta: float | None = None,
) -> Experiment:
    """Return a proposed baseline/minus/plus design; never send it to Marketplace."""
    if variable.name not in baseline.values:
        raise ValueError("The baseline must contain the selected variable.")
    if not variable.evidence or variable.provenance == "UNKNOWN":
        raise ValueError("A variable needs evidence and a non-UNKNOWN provenance before proposing experiments.")
    current = baseline.values[variable.name]
    if not isfinite(current):
        raise ValueError("Baseline values must be finite numbers.")
    step = delta if delta is not None else variable.step
    if step is None:
        step = max(abs(current) * 0.05, 1.0)
    if not isfinite(step) or step <= 0:
        raise ValueError("delta must be positive")
    minus = current - step
    plus = current + step
    if variable.minimum is not None:
        minus = max(minus, variable.minimum)
    if variable.maximum is not None:
        plus = min(plus, variable.maximum)
    perturbations = [Perturbation(variable.name, 0.0, "baseline")]
    if minus < current:
        perturbations.append(Perturbation(variable.name, minus - current, "minus"))
    if plus > current:
        perturbations.append(Perturbation(variable.name, plus - current, "plus"))
    return Experiment(
        experiment_id=f"ofat-{variable.name}-{metric}"[:96],
        baseline=baseline,
        variables=[variable],
        perturbations=perturbations,
        metrics=[metric],
        hypotheses=[f"Estimate the local response of {metric} to {variable.name}; this does not identify the internal Marketplace formula."],
    )
