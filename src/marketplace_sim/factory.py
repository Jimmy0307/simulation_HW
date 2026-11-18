"""Factory-side view of a quarter: operating capacity, overtime, lost sales and production cost (production scheduler).

Used to support the other departments' decisions: Marketing and Sales set brands, prices and a demand forecast; this
module answers what the factory does with them, at several demand outcomes and capacity settings.

Rules and their sources (levels in parentheses):

* Effective capacity = operating capacity (units/day) x 65 days x worker productivity (game help text and the
  OperatingCapacity screen: "effective operating capacity after adjustment for worker productivity") (derived).
* Overtime: up to 4 hours a day, used only when demand exceeds regular capacity; paid at the overtime labour change
  (+100 % on the Overtime screen); fatigue lowers productivity along the screen's curve, for the whole quarter
  (game help text; curve from the screen) (derived form, interpolated).
* Labour and overhead are paid for the scheduled operating capacity whether or not it is used (help text: "send
  production workers home while still paying them" = excess capacity cost). Their cost per unit at full use is the
  conversion part of the game's cost table at that volume (``cost_curve``) (estimated).
* The labour share of that conversion cost is not published per unit; ``labour_share`` is a labelled default read off
  the screen's labour/overhead graph shape (heuristic). It only matters for the overtime premium.
* Which volume the cost table means is an open question: ``reading="factory"`` uses the factory's total volume (the
  help text ties labour and overhead per unit to operating capacity, a factory-wide setting), ``reading="brand"``
  uses each brand's own volume. Run both until a settlement decides.
* The cost to change operating capacity (``minIncreaseCost`` + ``varIncreaseCPU`` x added units per quarter) is a
  reading of the screen parameters; the screen shows the figure but the formula is unverified (heuristic).

No game values live here: every number comes from the private pack and the caller's inputs.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from marketplace_sim.cost_curve import CurveCost, curve_cost, interpolate
from marketplace_sim.pack import ParamPack

DAYS = 65
REGULAR_HOURS = 8.0


@dataclass(frozen=True)
class BrandOrder:
    """One brand as Marketing/Sales decided it: price and forecast units (the order to the factory)."""

    name: str
    brand_type: str
    components: tuple[str, ...]
    price: float
    forecast: float


@dataclass(frozen=True)
class Schedule:
    operating_capacity: float  # units per day
    max_overtime_hours: float = 0.0  # 0..4
    productivity: float = 70.0  # percent, from HR
    previous_operating_capacity: float = 0.0


@dataclass
class FactoryResult:
    demand: float
    regular_capacity: float
    max_capacity: float
    produced: float
    lost: float
    overtime_hours_used: float
    productivity_used: float
    material_cost: float
    conversion_paid: float
    overtime_premium: float
    change_cost: float
    revenue: float
    idle_units: float
    unit_cost: float
    contribution: float  # revenue - production cost (all lines above)
    next_quarter_demand_cut: float  # fraction: half the unmet share (team's reading of the help file)
    notes: list[str] = field(default_factory=list)

    @property
    def production_cost(self) -> float:
        return self.material_cost + self.conversion_paid + self.overtime_premium + self.change_cost


def overtime_productivity(pack: ParamPack, hours: float, base: float) -> float:
    """Productivity after fatigue at ``hours`` of daily overtime, scaled to the base productivity (screen curve)."""
    curve = pack.extras.get("overtime_productivity") or []
    if not curve or hours <= 0:
        return base
    pts = sorted((float(h), float(p)) for h, p in curve)
    h0 = pts[0][1]
    for (xa, ya), (xb, yb) in itertools.pairwise(pts):
        if xa <= hours <= xb:
            p = ya + (yb - ya) * (hours - xa) / (xb - xa)
            return base * p / h0
    return base * pts[-1][1] / h0


def _capacity(oc: float, hours: float, productivity_pct: float) -> float:
    return oc * DAYS * (1 + hours / REGULAR_HOURS) * productivity_pct / 100


def run(pack: ParamPack, orders: Sequence[BrandOrder], schedule: Schedule, demand_factor: float = 1.0, *,
        reading: str = "factory", labour_share: float = 0.6, overtime_pay_change: float | None = None) -> FactoryResult:
    """One quarter of the factory for the given orders, schedule and demand outcome (multiple of the forecast)."""
    if reading not in ("factory", "brand"):
        raise ValueError("reading is 'factory' or 'brand'")
    fixed = float(pack.initial_state.get("fixed_capacity_units", 0.0))
    notes: list[str] = []
    oc = min(schedule.operating_capacity, fixed) if fixed else schedule.operating_capacity
    if oc < schedule.operating_capacity:
        notes.append("operating capacity capped at fixed capacity")
    p0 = schedule.productivity
    demand = {o.name: o.forecast * demand_factor for o in orders}
    total = sum(demand.values())
    regular = _capacity(oc, 0.0, p0)
    max_cap = _capacity(oc, schedule.max_overtime_hours, overtime_productivity(pack, schedule.max_overtime_hours, p0))
    if fixed:
        max_cap = min(max_cap, 1.5 * fixed * DAYS * p0 / 100)  # help text: overtime adds at most 50 % over fixed
    hours, prod_pct = 0.0, p0
    if total > regular and schedule.max_overtime_hours > 0:
        lo, hi = 0.0, schedule.max_overtime_hours  # smallest overtime that covers demand (bisection)
        for _ in range(40):
            mid = (lo + hi) / 2
            if _capacity(oc, mid, overtime_productivity(pack, mid, p0)) >= total:
                hi = mid
            else:
                lo = mid
        hours = hi
        prod_pct = overtime_productivity(pack, hours, p0)
    cap_used = min(_capacity(oc, hours, prod_pct), max_cap) if hours else regular
    produced_total = min(total, cap_used)
    share = produced_total / total if total else 0.0
    made = {name: d * share for name, d in demand.items()}

    def cost_at(order: BrandOrder, units: float) -> CurveCost | None:
        bt = pack.brand_type(order.brand_type)
        return curve_cost(pack, bt, [pack.component(c) for c in order.components], max(units, 1.0))

    # Labour and overhead are paid for the scheduled regular capacity; material for what is made.
    material = conversion = 0.0
    paid_units = max(regular, 1.0)
    for order in orders:
        units = made[order.name]
        basis = paid_units if reading == "factory" else max(regular * (order.forecast / max(sum(o.forecast for o in orders), 1e-9)), 1.0)
        c_mat = cost_at(order, produced_total if reading == "factory" else units)
        c_conv = cost_at(order, basis)
        if c_mat is None or c_conv is None:
            raise ValueError(f"no cost estimate for {order.name}")
        material += units * c_mat.material_part
        weight = (order.forecast / sum(o.forecast for o in orders)) if reading == "factory" else 1.0
        conversion += c_conv.conversion_part * (paid_units * weight if reading == "factory" else basis)
    conv_per_unit = conversion / paid_units
    ot_units = max(produced_total - regular, 0.0)
    pay_change = overtime_pay_change
    if pay_change is None:
        changes = [float(x.get("change", 0)) for x in pack.extras.get("overtime_labor_change", []) if x.get("overtime")]
        pay_change = (changes[0] if changes else 100.0) / 100
    premium = 0.0
    if hours > 0:
        fatigue = p0 / prod_pct - 1  # every regular unit now needs more labour time (paid within regular hours: fixed)
        premium = ot_units * conv_per_unit * (labour_share * (1 + pay_change) + (1 - labour_share)) * (1 + fatigue)
        notes.append(f"overtime used: {hours:.1f} h/day; productivity {prod_pct:.1f} %")
    added = max(oc - schedule.previous_operating_capacity, 0.0) * DAYS
    change = 0.0
    if added > 0:
        change = float(pack.production.get("min_increase_cost", 0.0)) + float(pack.production.get("var_increase_cpu", 0.0)) * added
    revenue = sum(made[o.name] * o.price for o in orders)
    cost = material + conversion + premium + change
    lost = total - produced_total
    return FactoryResult(
        demand=total, regular_capacity=regular, max_capacity=max_cap, produced=produced_total, lost=lost,
        overtime_hours_used=hours, productivity_used=prod_pct, material_cost=material, conversion_paid=conversion,
        overtime_premium=premium, change_cost=change, revenue=revenue, idle_units=max(regular - produced_total, 0.0),
        unit_cost=cost / produced_total if produced_total else math.inf, contribution=revenue - cost,
        next_quarter_demand_cut=0.5 * lost / total if total else 0.0, notes=notes)


def required_operating_capacity(forecast_units: float, productivity: float, buffer: float = 0.0) -> float:
    """Help-text rule: forecast / 65 days, grossed up for productivity, plus an optional buffer."""
    return forecast_units * (1 + buffer) / DAYS / (productivity / 100)


def sweep(pack: ParamPack, orders: Sequence[BrandOrder], operating_capacities: Sequence[float],
          overtime_hours: Sequence[float], demand_factors: Sequence[float], *, productivity: float = 70.0,
          reading: str = "factory", previous_operating_capacity: float = 0.0) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for oc in operating_capacities:
        for ot in overtime_hours:
            for f in demand_factors:
                r = run(pack, orders, Schedule(oc, ot, productivity, previous_operating_capacity), f, reading=reading)
                rows.append({"operating_capacity": oc, "max_overtime_hours": ot, "demand_factor": f, "reading": reading,
                             "demand": r.demand, "produced": r.produced, "lost": r.lost, "idle_units": r.idle_units,
                             "overtime_hours_used": r.overtime_hours_used, "unit_cost": r.unit_cost,
                             "production_cost": r.production_cost, "revenue": r.revenue,
                             "contribution": r.contribution, "next_quarter_demand_cut": r.next_quarter_demand_cut})
    return rows


__all__ = ["BrandOrder", "FactoryResult", "Schedule", "interpolate", "required_operating_capacity", "run", "sweep"]
