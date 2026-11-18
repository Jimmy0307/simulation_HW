"""Read-only, evidence-led Q2 factory-policy model.

Offline planning aid, NOT Marketplace's opaque PHP implementation.
Chart values, cost quotes and labour assumptions are caller-supplied;
nothing in this module reads auth data or writes game decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, log
from typing import Mapping, Sequence


def linear_interp(x: float, xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2 or any(xs[i] >= xs[i+1] for i in range(len(xs)-1)):
        raise ValueError("Need matched, ascending chart points")
    for i in range(len(xs)-1):
        if x <= xs[i+1]:
            return ys[i] + (ys[i+1]-ys[i])*(x-xs[i])/(xs[i+1]-xs[i])
    i = len(xs)-2
    return ys[i] + (ys[i+1]-ys[i])*(x-xs[i])/(xs[i+1]-xs[i])


def _natural_cubic(xs: Sequence[float], ys: Sequence[float], xx: float) -> float:
    """Pure-Python natural cubic, matching marketplace_sim.cost_curve's family."""
    n = len(xs)
    if n < 2:
        raise ValueError("At least two cost quotes required")
    if xx < xs[0] or xx > xs[-1] or n == 2:
        i = 0 if xx <= xs[0] else n-2 if xx >= xs[-1] else max(
            0, next((j for j in range(n-1) if xs[j] <= xx < xs[j+1]), 0))
        return ys[i] + (ys[i+1]-ys[i])*(xx-xs[i])/(xs[i+1]-xs[i])
    h = [xs[i+1]-xs[i] for i in range(n-1)]
    aa = [0.]*n; bb = [1.]*n; cc = [0.]*n; rr = [0.]*n
    for i in range(1,n-1):
        aa[i], bb[i], cc[i] = h[i-1], 2*(h[i-1]+h[i]), h[i]
        rr[i] = 6*((ys[i+1]-ys[i])/h[i]-(ys[i]-ys[i-1])/h[i-1])
    for i in range(1,n):
        w = aa[i]/bb[i-1]
        bb[i] -= w*cc[i-1]
        rr[i] -= w*rr[i-1]
    mm = [0.]*n
    mm[-1] = rr[-1]/bb[-1]
    for i in range(n-2,-1,-1):
        mm[i] = (rr[i]-cc[i]*mm[i+1])/bb[i]
    i = max(j for j in range(n-1) if xs[j] <= xx)
    left, right = xs[i+1]-xx, xx-xs[i]
    return ((mm[i]*left**3+mm[i+1]*right**3)/(6*h[i])
            +(ys[i]/h[i]-mm[i]*h[i]/6)*left
            +(ys[i+1]/h[i]-mm[i+1]*h[i]/6)*right)


def quote_cost(volume: float, points: Sequence[Sequence[float]]) -> float:
    """Natural cubic spline in log(volume), log(cost); extrapolation is uncertain."""
    if volume <= 0:
        return 0.
    x = [log(float(p[0])) for p in points]
    y = [log(float(p[1])) for p in points]
    if any(not isfinite(t) for t in x+y) or any(x[i]>=x[i+1] for i in range(len(x)-1)):
        raise ValueError("Invalid quote points")
    return exp(_natural_cubic(x,y,log(volume)))


@dataclass(frozen=True)
class FactoryEvidence:
    fixed_daily: int
    workdays: int
    productivity_pct: float
    overtime_hours: tuple[float, ...]
    overtime_productivity_pct: tuple[float, ...]
    daily_capacity_chart_x: tuple[float, ...]
    labor_per_unit_chart_y: tuple[float, ...]
    overhead_per_unit_chart_y: tuple[float, ...]
    quotes_by_brand: Mapping[str, Sequence[Sequence[float]]]

    def capacity(self, daily: int, hours: float, productivity_delta: float = 0.) -> float:
        pct = linear_interp(hours, self.overtime_hours, self.overtime_productivity_pct)
        return self.workdays*daily*(1+hours/8)*max(0,pct+productivity_delta)/100

    def schedule_cpu(self, daily: int) -> tuple[float, float]:
        x = self.daily_capacity_chart_x
        return (linear_interp(daily,x,self.labor_per_unit_chart_y),
                linear_interp(daily,x,self.overhead_per_unit_chart_y))


@dataclass(frozen=True)
class Policy:
    daily: int
    max_overtime_hours: int


@dataclass(frozen=True)
class PolicyAssumptions:
    idle_cost_per_slot: float = 100.
    chart_cost_weight: float = .5
    overtime_cost_weight: float = 1.
    future_stockout_margin_weight: float = .5
    reference_daily: int = 14
    starting_cash: float = 0.
    financing_cash: float = 0.
    interest_cash: float = 0.
    fixed_other_expenses: float = 0.
    planned_capex: float = 0.
    startup_cost: float = 0.
    startup_cost_per_daily_quarter_unit: float = 0.


def simulate(
    evidence: FactoryEvidence, policy: Policy, *,
    forecast_by_brand: Mapping[str,float],
    prices: Mapping[str,float],
    assumptions: PolicyAssumptions = PolicyAssumptions(),
) -> dict[str,float]:
    """JIT factory scenario. Never call this official Pro Forma output."""
    if not 1 <= policy.daily <= evidence.fixed_daily or not 0 <= policy.max_overtime_hours <= 4:
        raise ValueError("Policy exceeds captured equipment/overtime limits")
    if not forecast_by_brand or set(forecast_by_brand)-set(evidence.quotes_by_brand):
        raise ValueError("Missing brand quote")
    if any(x < 0 or not isfinite(x) for x in forecast_by_brand.values()):
        raise ValueError("Invalid demand")
    if set(forecast_by_brand)-set(prices):
        raise ValueError("Missing brand price")
    total = sum(forecast_by_brand.values())
    regular = evidence.capacity(policy.daily,0)
    maximum = evidence.capacity(policy.daily,policy.max_overtime_hours)
    served = min(total, maximum)
    missed = max(total-served,0.)
    lo = 0.; hi = float(policy.max_overtime_hours)
    if total <= regular:
        hi = 0.
    elif total < maximum:
        for _ in range(40):
            m = (lo+hi)/2
            if evidence.capacity(policy.daily,m) >= served:
                hi = m
            else:
                lo = m
    used_hours = hi
    labor, overhead = evidence.schedule_cpu(policy.daily)
    ref_labor, ref_overhead = evidence.schedule_cpu(assumptions.reference_daily)
    revenue = 0.; production = 0.; missed_contribution = 0.
    for brand, volume in forecast_by_brand.items():
        share = volume/total if total else 0
        actual = share*served
        # Crucial: the server cost quote volume is TOTAL company production.
        unit = quote_cost(served, evidence.quotes_by_brand[brand])
        revenue += actual*prices[brand]
        production += actual*unit
        missed_contribution += (volume-actual)*max(prices[brand]-unit,0.)
    # Quoted costs already contain some labor/overhead; only the observed
    # DIFFERENCE from the reference schedule is applied, with sensitivity weight.
    unit_adjust = (labor+overhead-ref_labor-ref_overhead)*assumptions.chart_cost_weight*served
    idle = max(regular-served,0)*assumptions.idle_cost_per_slot
    overtime_extra = regular*labor*2*(used_hours/8)*assumptions.overtime_cost_weight
    setup = assumptions.startup_cost + assumptions.startup_cost_per_daily_quarter_unit*evidence.workdays*policy.daily
    cash = (assumptions.starting_cash+assumptions.financing_cash+assumptions.interest_cash+
            revenue-production-unit_adjust-idle-overtime_extra-setup-
            assumptions.fixed_other_expenses-assumptions.planned_capex)
    return {
        "forecast_units": total, "production_units": served, "stockout_units": missed,
        "regular_capacity_units": regular, "maximum_capacity_units": maximum,
        "overtime_hours_used": used_hours,
        "idle_regular_slots": max(regular-served,0),
        "revenue_est": revenue, "direct_production_cost_est": production,
        "chart_cost_difference_est": unit_adjust, "idle_cost_est": idle,
        "overtime_cost_est": overtime_extra, "cash_est": cash,
        "cash_plus_optional_future_goodwill": cash-missed_contribution*assumptions.future_stockout_margin_weight,
        "is_official_factory_result": False,
    }
