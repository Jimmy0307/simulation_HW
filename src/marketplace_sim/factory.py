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
  production workers home while still paying them" = excess capacity cost): the conversion part of the game's cost
  table at the effective volume, times the PLANNED units (operating capacity x 65 days). Per unit made at full use that
  is the table rate / productivity. Checked once: the Q2 Production Simulation's excess-capacity charge at zero demand
  is reproduced within 0.2 % (estimated; one point).
* The labour share of that conversion cost is not published per unit; ``labour_share`` is a labelled default read off
  the screen's labour/overhead graph shape (heuristic). It only matters for the overtime premium.
* The cost table's volumes are the total units produced across all brands: the Cost of Production screen says so in
  its column header and instructions ("look for the column under the total number of units you expect to sell across
  all brands"). ``reading="factory"`` (default) follows it; ``reading="brand"`` (each brand's own volume) is kept only
  as a what-if.
* The cost to change operating capacity (``minIncreaseCost`` + ``varIncreaseCPU`` x added units per quarter) is a
  reading of the screen parameters; the screen shows the figure but the formula is unverified (heuristic).

With the game's factory screens in a private pack (``extras.factory_screen``: labour and overhead per unit of
effective capacity, the capacity change cost and the material volume factor, all read at one operating capacity),
``_run_on_screen`` prices the quarter the way the Production Simulation does. At the operating capacity they were read
at, it reproduces the screen's per-brand Production Average and its excess-capacity charge (Q2: 50 / 100 / 150 % of
the forecast, within rounding). ``factory_screen.points`` may add the OperatingCapacity screen read at other
capacities (labour and overhead per unit, change cost); a capacity that was read uses its own rates. At capacities
not read, the rates follow the cost table's curve from the nearest capacity read (estimated).

No game values live here: every number comes from the private pack and the caller's inputs.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from marketplace_sim.cost_curve import CurveCost, curve_cost, interpolate
from marketplace_sim.pack import ParamPack

DAYS = 65
REGULAR_HOURS = 8.0
DEFAULT_PRODUCTIVITY = 70.0  # percent; help text: first quarter, standard compensation package


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
    productivity: float = DEFAULT_PRODUCTIVITY  # percent, from HR
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
    conversion_per_unit: float = 0.0  # labour + overhead per unit of scheduled regular capacity
    made: dict[str, float] = field(default_factory=dict)  # units made per brand
    material_by_brand: dict[str, float] = field(default_factory=dict)  # material cost per unit, per brand
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
        reading: str = "factory", labour_share: float = 0.6, overtime_pay_change: float | None = None,
        fixed_capacity: float | None = None) -> FactoryResult:
    """One quarter of the factory for the given orders, schedule and demand outcome (multiple of the forecast).

    ``fixed_capacity`` (units/day) is the capacity owned this quarter; default: the pack's starting capacity.
    """
    if reading not in ("factory", "brand"):
        raise ValueError("reading is 'factory' or 'brand'")
    fixed = float(pack.initial_state.get("fixed_capacity_units", 0.0) if fixed_capacity is None else fixed_capacity)
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
    screen = pack.extras.get("factory_screen")
    if screen and reading == "factory":
        return _run_on_screen(pack, orders, schedule, screen, demand, total, regular, max_cap, hours, prod_pct, made,
                              produced_total, notes, cost_at, overtime_pay_change)
    material = conversion = 0.0
    paid_units = max(regular, 1.0)
    material_by_brand: dict[str, float] = {}
    for order in orders:
        units = made[order.name]
        basis = paid_units if reading == "factory" else max(regular * (order.forecast / max(sum(o.forecast for o in orders), 1e-9)), 1.0)
        c_mat = cost_at(order, produced_total if reading == "factory" else units)
        c_conv = cost_at(order, basis)
        if c_mat is None or c_conv is None:
            raise ValueError(f"no cost estimate for {order.name}")
        material += units * c_mat.material_part
        material_by_brand[order.name] = c_mat.material_part
        forecast_sum = sum(o.forecast for o in orders)
        weight = (order.forecast / forecast_sum if forecast_sum else 1.0 / len(orders)) if reading == "factory" else 1.0
        conversion += c_conv.conversion_part * (paid_units * weight if reading == "factory" else basis)
    # Labour and overhead are paid on the planned capacity (operating capacity x 65 days), at the table's rate for the
    # effective volume: the game's excess-capacity charge at zero demand equals that product (one Q2 screen point).
    # Per unit actually made, the conversion cost is therefore the table rate / productivity.
    conversion *= 100.0 / p0
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
        next_quarter_demand_cut=0.5 * lost / total if total else 0.0, conversion_per_unit=conv_per_unit,
        made=made, material_by_brand=material_by_brand, notes=notes)


def _log_interp(points: Sequence[Sequence[float]], x: float) -> float:
    pts = sorted((float(a), float(b)) for a, b in points)
    if len(pts) == 1:
        return pts[0][1]
    lx = math.log(max(x, 1.0))
    for (xa, ya), (xb, yb) in itertools.pairwise(pts):
        if lx <= math.log(xb) or (xb, yb) == pts[-1]:
            t = (lx - math.log(xa)) / (math.log(xb) - math.log(xa))
            return ya + (yb - ya) * t
    return pts[-1][1]


def _run_on_screen(pack: ParamPack, orders: Sequence[BrandOrder], schedule: Schedule, screen: dict[str, Any],
                   demand: dict[str, float], total: float, regular: float, max_cap: float, hours: float, prod_pct: float,
                   made: dict[str, float],
                   produced_total: float, notes: list[str], cost_at: object, overtime_pay_change: float | None
                   ) -> FactoryResult:
    """Costs from the game's own factory screens (OperatingCapacity, Overtime, Production Simulation), private pack.

    ``screen`` (all measured at one operating capacity ``oc``): ``labour_per_unit`` and ``overhead_per_unit`` of
    effective capacity, ``change_cost`` (from zero to ``oc``), ``material_factor`` = [[total units, factor of the
    component sum], ...]. Labour is paid on effective regular capacity, plus overtime hours at the pay change;
    overhead per unit made (idle units too); the change cost is spread over effective capacity. At another operating
    capacity the labour and overhead rates follow the cost table's conversion curve (one-point scaling, estimated).
    """
    oc, p0 = schedule.operating_capacity, schedule.productivity
    base_oc = float(screen["oc"])
    read = [screen, *screen.get("points", [])]  # the OperatingCapacity screen, read at one or more capacities
    point = min(read, key=lambda q: (abs(float(q["oc"]) - oc), float(q["oc"])))
    lr, ob = float(point["labour_per_unit"]), float(point["overhead_per_unit"])
    if oc != float(point["oc"]) and pack.cost_estimates:
        o0 = orders[0]
        bt = pack.brand_type(o0.brand_type)
        comps = [pack.component(c) for c in o0.components]
        ref = curve_cost(pack, bt, comps, float(point["oc"]) * DAYS * p0 / 100)
        here = curve_cost(pack, bt, comps, max(oc * DAYS * p0 / 100, 1.0))
        if ref is not None and here is not None and ref.conversion_part > 0:
            scale = here.conversion_part / ref.conversion_part
            lr, ob = lr * scale, ob * scale
            notes.append(f"labour and overhead rates scaled from the screen read at {float(point['oc']):g}/day by the "
                         f"cost table's curve (x{scale:.3f}); estimated")
    added = max(oc - schedule.previous_operating_capacity, 0.0)
    min_inc = float(pack.production.get("min_increase_cost", 0.0))
    change = 0.0
    if added > 0:
        if oc == float(point["oc"]) and schedule.previous_operating_capacity == 0 and "change_cost" in point:
            change = float(point["change_cost"])
        else:
            per_unit = (float(screen["change_cost"]) - min_inc) / (base_oc * DAYS) if base_oc else 0.0
            change = min_inc + per_unit * added * DAYS
    eff = max(regular, 1.0)
    pay_change = overtime_pay_change
    if pay_change is None:
        changes = [float(x.get("change", 0)) for x in pack.extras.get("overtime_labor_change", []) if x.get("overtime")]
        pay_change = (changes[0] if changes else 100.0) / 100
    labour_regular = lr * eff
    premium = labour_regular * (1 + pay_change) * hours / REGULAR_HOURS
    # The game spreads the change cost over effective regular capacity: every unit made carries change / eff, so a
    # quarter on overtime carries a little more than the change cost itself (Q2 screen at 150 %).
    overhead = ob * max(produced_total, eff) + change * (max(produced_total, eff) / eff - 1)
    factors = screen.get("material_factor") or [[1.0, 1.0]]
    factor = _log_interp(factors, produced_total)
    material_by_brand = {o.name: sum(pack.component(c).price for c in o.components)
                         * pack.brand_type(o.brand_type).cost_adj * factor for o in orders}
    material = sum(made[o.name] * material_by_brand[o.name] for o in orders)
    conversion = labour_regular + overhead
    idle = max(regular - produced_total, 0.0)
    idle_rate = lr + ob + change / eff
    revenue = sum(made[o.name] * o.price for o in orders)
    cost = material + conversion + premium + change
    if hours > 0:
        notes.append(f"overtime used: {hours:.1f} h/day; productivity {prod_pct:.1f} %")
    lost = total - produced_total
    return FactoryResult(
        demand=total, regular_capacity=regular, max_capacity=max_cap, produced=produced_total, lost=lost,
        overtime_hours_used=hours, productivity_used=prod_pct, material_cost=material, conversion_paid=conversion,
        overtime_premium=premium, change_cost=change, revenue=revenue, idle_units=idle,
        unit_cost=cost / produced_total if produced_total else math.inf, contribution=revenue - cost,
        next_quarter_demand_cut=0.5 * lost / total if total else 0.0, conversion_per_unit=idle_rate,
        made=made, material_by_brand=material_by_brand, notes=notes)


def required_operating_capacity(forecast_units: float, productivity: float, buffer: float = 0.0) -> float:
    """Help-text rule: forecast / 65 days, grossed up for productivity, plus an optional buffer."""
    return forecast_units * (1 + buffer) / DAYS / (productivity / 100)


def sweep(pack: ParamPack, orders: Sequence[BrandOrder], operating_capacities: Sequence[float],
          overtime_hours: Sequence[float], demand_factors: Sequence[float], *, productivity: float = DEFAULT_PRODUCTIVITY,
          reading: str = "factory", previous_operating_capacity: float = 0.0,
          fixed_capacity: float | None = None) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for oc in operating_capacities:
        for ot in overtime_hours:
            for f in demand_factors:
                r = run(pack, orders, Schedule(oc, ot, productivity, previous_operating_capacity), f, reading=reading,
                        fixed_capacity=fixed_capacity)
                rows.append({"operating_capacity": oc, "max_overtime_hours": ot, "demand_factor": f, "reading": reading,
                             "demand": r.demand, "produced": r.produced, "lost": r.lost, "idle_units": r.idle_units,
                             "overtime_hours_used": r.overtime_hours_used, "unit_cost": r.unit_cost,
                             "production_cost": r.production_cost, "revenue": r.revenue,
                             "contribution": r.contribution, "next_quarter_demand_cut": r.next_quarter_demand_cut})
    return rows


def expected_values(rows: Sequence[dict[str, float | str]], weights: dict[float, float], lost_share_value: float
                    ) -> list[dict[str, float]]:
    """Per schedule: probability-weighted contribution minus the value of next quarter's demand cut.

    ``weights`` maps demand factor -> probability (normalised here); ``lost_share_value`` = what one full share of
    next quarter's demand is worth (e.g. next quarter's forecast x margin per unit). Assumptions are the caller's.
    """
    total = sum(weights.values()) or 1.0
    out: dict[tuple[float, float], dict[str, float]] = {}
    for r in rows:
        f = float(r["demand_factor"])
        if f not in weights:
            continue
        key = (float(r["operating_capacity"]), float(r["max_overtime_hours"]))
        item = out.setdefault(key, {"operating_capacity": key[0], "max_overtime_hours": key[1], "expected_value": 0.0,
                                    "worst_contribution": math.inf, "max_lost": 0.0})
        value = float(r["contribution"]) - float(r["next_quarter_demand_cut"]) * lost_share_value
        item["expected_value"] += weights[f] / total * value
        item["worst_contribution"] = min(item["worst_contribution"], float(r["contribution"]))
        item["max_lost"] = max(item["max_lost"], float(r["lost"]))
    return sorted(out.values(), key=lambda x: -x["expected_value"])


__all__ = ["DEFAULT_PRODUCTIVITY", "BrandOrder", "FactoryResult", "Schedule", "expected_values", "interpolate", "required_operating_capacity", "run", "sweep"]
