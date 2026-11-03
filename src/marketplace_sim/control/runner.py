"""run_scenario(spec): deterministic multi-quarter execution with events, overrides, competitors and a policy."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from marketplace_sim import modules as m
from marketplace_sim.control.events import apply_events
from marketplace_sim.control.spec import CompetitorSpec, ScenarioSpec, apply_overrides
from marketplace_sim.engine import CompanyState, Plan, advance
from marketplace_sim.pack import pack_from_dict
from marketplace_sim.provenance import Level

RESULT_SCHEMA = "marketplace-sim/scenario-result@1"
KEY_OUTPUTS = ("cash_end", "net_income", "revenue", "market_share", "capex_capacity", "production_cost", "capacity_units_per_quarter")


class _PriceScaledBot:
    """Wraps a bot to apply a constant price multiplier from its spec params (e.g. an aggressive pricer)."""

    def __init__(self, inner: m.Competitor, factor: float) -> None:
        self.inner, self.factor = inner, factor

    def offers(self, pack: Any, quarter: int, rng: Any) -> list[m.Offer]:
        from dataclasses import replace

        return [replace(o, price=o.price * self.factor) for o in self.inner.offers(pack, quarter, rng)]


def build_competitor(spec: CompetitorSpec, scenario: ScenarioSpec) -> m.Competitor:
    bot: m.Competitor
    if spec.strategy == "baseline":
        bot = m.BaselineBot(spec.name)
    elif spec.strategy == "random":
        bot = m.RandomBot(spec.name)
    elif spec.strategy == "replay":
        panel_path = scenario.resolve(str(spec.params.get("panel", "")))
        text = panel_path.read_text(encoding="utf-8")
        panel = json.loads(text)
        if "private" not in panel_path.resolve().as_posix().split("/") and not panel.get("synthetic"):
            raise ValueError("replay panels with real decisions must live under a 'private' directory")
        offers = {int(q): [m.Offer(o["firm"], o["brand"], str(o["segment_id"]), float(o["price"]), float(o.get("fit", 1)),
                                   float(o.get("advertising", 0)), frozenset(o.get("markets", [])))
                           for o in rows] for q, rows in panel["quarters"].items()}
        bot = m.ReplayCompetitors(offers)
    else:
        raise ValueError(f"unknown competitor strategy '{spec.strategy}'")
    factor = float(spec.params.get("price_factor", 1.0))
    return _PriceScaledBot(bot, factor) if factor != 1.0 else bot


def _plan_for(spec: ScenarioSpec, quarter: int) -> tuple[Plan, str]:
    policy = spec.our_policy
    kind = policy.get("type", "hold")
    if kind == "hold":
        return Plan(name="hold"), "hold"
    if kind in {"fixed", "repeat"}:
        plans = {int(k): v for k, v in (policy.get("plans") or {}).items()}
        ref = plans.get(quarter, policy.get("default"))
    elif kind == "external":
        candidate = spec.resolve(str(policy.get("dir", "."))) / f"q{quarter}.yaml"
        ref = str(candidate) if candidate.exists() else None
    else:
        raise ValueError(f"unknown policy type '{kind}'")
    if not ref:
        return Plan(name="hold"), "hold (no plan for this quarter)"
    path = spec.resolve(str(ref))
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Plan.from_dict(data, name=path.stem), str(ref)


@dataclass
class QuarterResult:
    quarter: int
    plan: str
    events: list[str]
    overrides: list[str]
    lines: dict[str, dict[str, Any]]
    notes: list[str]
    state: dict[str, Any]


@dataclass
class ScenarioResult:
    name: str
    fingerprint: str
    seed: int
    quarters: list[QuarterResult] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        def series(metric: str) -> list[dict[str, Any]]:
            return [q.lines[metric] for q in self.quarters if metric in q.lines]

        cash = series("cash_end")
        net = series("net_income")
        weakest = {
            metric: min((Level[x["level"].upper()] for x in series(metric)), default=Level.VERIFIED).label
            for metric in KEY_OUTPUTS if series(metric)
        }
        return {
            "final_cash": cash[-1]["value"] if cash else None,
            "min_cash": min(x["value"] for x in cash) if cash else None,
            "cumulative_net_income": sum(x["value"] for x in net),
            "total_capex": sum(x["value"] for x in series("capex_capacity")),
            "emergency_loans": sum(x["value"] for x in series("emergency_loan")),
            "weakest_level": weakest,
            "quarters_with_events": [q.quarter for q in self.quarters if q.events],
        }

    def to_dict(self) -> dict[str, Any]:
        return {"schema": RESULT_SCHEMA, "name": self.name, "fingerprint": self.fingerprint, "seed": self.seed,
                "summary": self.summary(), "quarters": [q.__dict__ for q in self.quarters]}


def run_scenario(spec: ScenarioSpec) -> ScenarioResult:
    pack_dir = spec.resolve(spec.base_params)
    pack_text = (pack_dir / "pack.json").read_text(encoding="utf-8")
    raw = json.loads(pack_text)
    competitors = [build_competitor(c, spec) for c in spec.competitors] if spec.competitors else None
    result = ScenarioResult(spec.name, spec.fingerprint(pack_text), spec.seed)
    state = CompanyState.initial(pack_from_dict(raw, pack_dir / "pack.json"), spec.start_quarter)
    for quarter in range(spec.start_quarter, spec.start_quarter + spec.horizon):
        data, overrides_applied = apply_overrides(raw, spec.overrides, quarter)
        data, adjust = apply_events(data, spec.events, quarter)
        pack = pack_from_dict(data, pack_dir / "pack.json")
        plan, plan_ref = _plan_for(spec, quarter)
        state, report = advance(state, plan, pack, competitors=competitors, seed=spec.seed, adjust=adjust)
        result.quarters.append(QuarterResult(quarter, plan_ref, list(adjust.labels), overrides_applied,
                                             report.to_dict()["lines"], report.notes, state.to_dict()))
    return result


def write_result(result: ScenarioResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result.name}.result.json"
    path.write_text(json.dumps(result.to_dict(), indent=1, ensure_ascii=False), encoding="utf-8")
    return path
