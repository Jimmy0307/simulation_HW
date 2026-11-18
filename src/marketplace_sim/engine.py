"""Quarter advance: company state + decisions -> next state + tagged report."""

from __future__ import annotations

import copy
import random
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from marketplace_sim import modules as m
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged, const, total


@dataclass
class Brand:
    name: str
    brand_type: str
    components: list[str]
    segment_id: str | None = None


@dataclass
class CompanyState:
    quarter: int
    cash: float
    cd: float
    fixed_capacity_units: float
    stores_open: list[str] = field(default_factory=list)
    web_centers_open: list[str] = field(default_factory=list)
    brands: dict[str, Brand] = field(default_factory=dict)
    inventory: dict[str, float] = field(default_factory=dict)
    stock_total: float = 0.0
    shares_total: float = 0.0
    pending_capacity_units: float = 0.0
    cash_level: str = "verified"  # level of the cash balance carried from the previous quarter
    ad_stock: dict[str, float] = field(default_factory=dict)  # advertising goodwill per brand (literature demand)
    module_state: dict[str, dict[str, float]] = field(default_factory=dict)  # business-module state (sales force ...)
    operating_capacity: float = 0.0  # units/day scheduled last quarter (just-in-time factory)
    demand_cut: float = 0.0  # share of our demand lost this quarter because of last quarter's stock-outs

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompanyState:
        data = dict(data)
        data["brands"] = {k: Brand(**v) for k, v in data.get("brands", {}).items()}
        return cls(**data)

    @classmethod
    def initial(cls, pack: ParamPack, quarter: int = 1) -> CompanyState:
        init = pack.initial_state
        return cls(quarter=quarter, cash=init.get("cash", 0.0), cd=init.get("cd", 0.0),
                   fixed_capacity_units=init.get("fixed_capacity_units", 0.0),
                   stores_open=[s.key for s in pack.stores if s.opened],
                   web_centers_open=[w.key for w in pack.web_centers if w.opened],
                   stock_total=init.get("stock_total", 0.0), shares_total=init.get("shares_total", 0.0))


@dataclass
class BrandPlan:
    name: str
    brand_type: str
    price: float = 0.0
    production: float = 0.0
    advertising: float = 0.0
    components: list[str] | None = None
    segment: str | None = None


@dataclass
class Plan:
    name: str = "plan"
    capacity_increase: float = 0.0
    cd_deposit: float = 0.0
    cd_withdraw: float = 0.0
    open_stores: list[str] = field(default_factory=list)
    open_web_centers: list[str] = field(default_factory=list)
    stock_issue: list[tuple[float, float]] = field(default_factory=list)
    brands: list[BrandPlan] = field(default_factory=list)
    modules: dict[str, Any] = field(default_factory=dict)  # business-module decisions, keyed like the ledger
    factory: dict[str, float] | None = None  # just-in-time factory: operating_capacity, max_overtime_hours, productivity

    @classmethod
    def from_dict(cls, data: dict[str, Any], name: str = "plan") -> Plan:
        cd = data.get("cd") or {}
        return cls(
            name=str(data.get("name", name)),
            capacity_increase=float(data.get("capacity_increase", 0)),
            cd_deposit=float(cd.get("deposit", 0)), cd_withdraw=float(cd.get("withdraw", 0)),
            open_stores=[str(x) for x in data.get("open_stores", [])],
            open_web_centers=[str(x) for x in data.get("open_web_centers", [])],
            stock_issue=[(float(x["shares"]), float(x["price"])) for x in data.get("stock_issue", [])],
            brands=[BrandPlan(name=str(b["name"]), brand_type=str(b["brand_type"]), price=float(b.get("price", 0)),
                              production=float(b.get("production", 0)), advertising=float(b.get("advertising", 0)),
                              components=[str(c) for c in b["components"]] if b.get("components") else None,
                              segment=None if b.get("segment") is None else str(b["segment"]))
                    for b in data.get("brands", [])],
            modules=dict(data.get("modules") or {}),
            factory={k: float(v) for k, v in data["factory"].items()} if data.get("factory") else None,
        )


@dataclass
class Report:
    quarter: int
    plan: str
    lines: dict[str, Tagged]
    notes: list[str]

    def render(self) -> str:
        width = max(len(k) for k in self.lines) if self.lines else 10
        rows = [f"Quarter {self.quarter} - plan '{self.plan}'   [V]=verified [D]=derived [E]=estimated [P]=placeholder",
                "-" * (width + 30)]
        rows += [f"{k.ljust(width)}  {v.render():>24}" for k, v in self.lines.items()]
        rows += [f"note: {n}" for n in self.notes]
        return "\n".join(rows)

    def to_dict(self) -> dict[str, Any]:
        return {"quarter": self.quarter, "plan": self.plan, "notes": self.notes,
                "lines": {k: {"value": v.value, "level": v.level.label, "source": v.source} for k, v in self.lines.items()}}


@dataclass
class Adjustments:
    """Scenario-level adjustments applied by the control plane (events). Defaults change nothing."""

    capacity_factor: float = 1.0
    rival_price_factor: dict[str, float] = field(default_factory=dict)  # firm name or "*" -> multiplier
    labels: list[str] = field(default_factory=list)


def advance(state: CompanyState, plan: Plan, pack: ParamPack, *, demand: m.DemandModel | None = None,
            competitors: list[m.Competitor] | None = None, seed: int = 0,
            adjust: Adjustments | None = None) -> tuple[CompanyState, Report]:
    """Apply one quarter of decisions. Returns the next state and a fully tagged report."""
    from marketplace_sim.business import BrandInput, run_modules
    from marketplace_sim.business.base import Outcome
    from marketplace_sim.demand import demand_for

    demand = demand or demand_for(pack)
    carryover = float(getattr(demand, "carryover", 0.0))
    web_weight = float((getattr(demand, "coefficients", None) or {}).get("web_weight", 1.0))
    competitors = competitors if competitors is not None else [m.BaselineBot("bot-a"), m.RandomBot("bot-b")]
    adjust = adjust or Adjustments()
    rng = random.Random(seed * 1009 + state.quarter)
    new = copy.deepcopy(state)
    lines: dict[str, Tagged] = {}
    notes: list[str] = [f"event: {label}" for label in adjust.labels]
    start_cash = const(state.cash, Level[state.cash_level.upper()], "cash at quarter start (carried state)")
    lines["cash_start"] = start_cash

    # Capacity bought now becomes usable next quarter (screen semantics "next quarter capacity": derived).
    jit = plan.factory is not None
    if jit and ("production.operating_capacity" in plan.modules or "production.excess_capacity" in plan.modules):
        raise ValueError("the factory block replaces the operating-capacity and excess-capacity modules: use one")
    lines["capex_capacity"] = m.capacity_purchase(pack, plan.capacity_increase)
    lines["capacity_units_per_quarter"] = m.quarterly_capacity(pack, state.fixed_capacity_units)
    if adjust.capacity_factor != 1.0:
        lines["capacity_units_per_quarter"] = lines["capacity_units_per_quarter"].scaled(
            adjust.capacity_factor, f"scenario capacity factor {adjust.capacity_factor:g}")

    stores_before, web_before = set(state.stores_open), set(state.web_centers_open)
    lines["store_setup"] = m.opening_cost(pack.stores, plan.open_stores, stores_before, "stores")
    lines["web_center_setup"] = m.opening_cost(pack.web_centers, plan.open_web_centers, web_before, "web centers")
    lines["outlet_lease"] = m.recurring_lease(pack.stores, stores_before) + m.recurring_lease(pack.web_centers, web_before)
    new.stores_open = sorted(stores_before | set(plan.open_stores))
    new.web_centers_open = sorted(web_before | set(plan.open_web_centers))

    cd_balance, interest = m.cd_quarter(pack, state.cd, plan.cd_deposit, plan.cd_withdraw)
    lines["cd_balance"], lines["cd_interest"] = cd_balance, interest
    new.cd = cd_balance.value
    cd_flow = Tagged(plan.cd_withdraw - plan.cd_deposit, Level.VERIFIED, "withdraw - deposit")

    stock_raised, shares_added = m.stock_raise(plan.stock_issue, state.stock_total, state.shares_total)
    lines["stock_raised"] = stock_raised
    new.stock_total, new.shares_total = state.stock_total + stock_raised.value, state.shares_total + shares_added.value

    # Brands, production and sales (placeholder economics).
    new_brand_count = 0
    production_cost: list[Tagged] = []
    own_offers: list[m.Offer] = []
    capacity_left = lines["capacity_units_per_quarter"].value
    market_reach = m.reach(pack, stores_before, web_before)
    market_coverage = tuple(sorted(m.coverage(pack, stores_before, web_before, web_weight).items()))
    # Business modules (marketplace_sim.business): their effects enter at fixed coupling points; the weakest level
    # of the demand couplings is applied to everything downstream of demand, cost couplings carry their own level.
    # No module decided or carried = nothing changes.
    outlets = len(stores_before) + len(web_before)
    effects = run_modules(pack, quarter=state.quarter, decisions=plan.modules, carried=state.module_state,
                          brands=[BrandInput(bp.name, bp.advertising, bp.production, bp.price, _segment(pack, state, bp))
                                  for bp in plan.brands],
                          markets_reached=len(market_reach), inventory=state.inventory,
                          web_share=len(web_before) / outlets if outlets else 0.0, capacity_units=capacity_left)
    if effects.capacity_level is not None:  # shifts, overtime, productivity (business modules)
        base_cap = lines["capacity_units_per_quarter"]
        factor = effects.capacity_factor.value if effects.capacity_factor is not None else 1.0
        extra = effects.capacity_extra.value if effects.capacity_extra is not None else 0.0
        lines["capacity_units_per_quarter"] = Tagged(base_cap.value * factor + extra,
                                                     min(base_cap.level, effects.capacity_level),
                                                     f"{base_cap.source} x module capacity factor + module extra units")
        capacity_left = lines["capacity_units_per_quarter"].value
    demand_level = demand.level if effects.demand_level is None else min(demand.level, effects.demand_level)
    if effects.active:
        level_note = f"demand-chain level {effects.demand_level.label}" if effects.demand_level is not None else \
            "no demand coupling"
        notes.append(f"business modules active: {', '.join(effects.active)} ({level_note}; every number downstream "
                     "takes the weakest level of what it uses)")
        notes.extend(effects.notes)
    effort = effects.selling_effort.value if effects.selling_effort is not None else 1.0
    released: dict[str, Tagged] = {}
    for brand_name, out_units in effects.inventory_release.items():  # sell-off at quarter start
        new.inventory[brand_name] = new.inventory.get(brand_name, 0.0) - out_units.value
        released[brand_name] = out_units
    units_level: dict[str, Level] = {}  # below VERIFIED only when a module rule or a module capacity decided units
    unit_costs: dict[str, Tagged] = {}
    produced_units: dict[str, float] = {}
    ordered = plan.brands
    planned_total = min(sum(max(bp.production, 0.0) for bp in plan.brands), capacity_left)
    if effects.production_order is not None:
        rank = {name: i for i, name in enumerate(effects.production_order)}
        ordered = sorted(plan.brands, key=lambda b: rank.get(b.name, len(rank)))
    for bp in ordered:
        bt = pack.brand_type(bp.brand_type)
        if bp.name not in new.brands:
            comps = [pack.component(c) for c in bp.components] if bp.components else m.default_components(pack, bt)
            new.brands[bp.name] = Brand(bp.name, bt.code, [c.id for c in comps], bp.segment or bt.segment_id)
            new_brand_count += 1
        brand = new.brands[bp.name]
        rule = effects.production_units.get(bp.name)
        wanted = rule.value if rule is not None else bp.production
        if jit:  # just-in-time: production follows demand, set after demand below
            if bp.production:
                notes.append(f"{bp.name}: planned production ignored (just-in-time factory builds what is demanded)")
            wanted, rule = 0.0, None
        if rule is not None:
            units_level[bp.name] = rule.level
        units = min(wanted, capacity_left)
        # The game's cost table is per quarter volume. Default reading: the factory's total volume (help text: labour
        # and overhead per unit follow operating capacity); a private pack may set extras.cost_reading = "brand".
        own = units if units > 0 else bp.production
        cost = _unit_cost(pack, new, bp.name, effects,
                          volume=own if pack.extras.get("cost_reading") == "brand" else max(planned_total, own))
        lines[f"unit_cost[{bp.name}]"] = cost
        unit_costs[bp.name] = cost
        if units < wanted:
            notes.append(f"{bp.name}: production capped by capacity ({units:.0f} of {wanted:.0f})")
            if effects.capacity_level is not None:
                units_level[bp.name] = min(units_level.get(bp.name, Level.VERIFIED), effects.capacity_level)
        capacity_left -= units
        produced_units[bp.name] = units
        new.inventory[bp.name] = new.inventory.get(bp.name, 0.0) + units
        if units > 0 and not jit:  # nothing produced costs nothing, whatever the (unverified) unit-cost rule says
            batch = cost.scaled(units, f"{units:.0f} units")
            if bp.name in units_level:
                batch = batch.with_level(units_level[bp.name], f"{batch.source} (units set by a module rule)")
            production_cost.append(batch)
        segment = brand.segment_id or (pack.segments[0].id if pack.segments else "")
        stock = carryover * state.ad_stock.get(bp.name, 0.0) + max(bp.advertising, 0.0)
        new.ad_stock[bp.name] = stock
        split = effects.media_split.get(bp.name)
        brand_effort = effort
        if bp.name in effects.attraction:
            brand_effort = effort * effects.attraction[bp.name].value
        price_factor = effects.price_factor[bp.name].value if bp.name in effects.price_factor else 1.0
        if bp.price > 0 and market_reach:
            own_offers.append(m.Offer("us", bp.name, segment, bp.price, m.segment_fit(bt, segment), bp.advertising,
                                      market_reach, position=bt.segment_id, quality=1.0, ad_stock=stock,
                                      coverage=market_coverage, effort=brand_effort, media=split.parts if split else (),
                                      price_factor=price_factor))
    lines["design_cost"] = m.design_cost(pack, new_brand_count)
    lines["production_cost"] = total(production_cost, "sum(units x unit_cost)", empty_level=Level.VERIFIED)
    lines["advertising"] = const(sum(b.advertising for b in plan.brands), Level.VERIFIED, "plan input")
    lines.update(effects.lines)
    lines.update(effects.expenses)

    rival_offers = [o for c in competitors for o in c.offers(pack, state.quarter, rng)]
    if adjust.rival_price_factor:
        rival_offers = [replace(o, price=o.price * adjust.rival_price_factor.get(o.firm, adjust.rival_price_factor.get("*", 1.0)))
                        for o in rival_offers]
    demanded = demand.units(pack, own_offers + rival_offers)
    if effects.demand_level is not None:
        why = f" · with business modules {', '.join(effects.active)} ({effects.demand_level.label})"
        demanded = {k: v.with_level(effects.demand_level, v.source + why) for k, v in demanded.items()}
    if state.demand_cut > 0:  # last quarter's stock-outs (heuristic: half the unmet share, team's reading of the help file)
        demanded = {k: (Tagged(v.value * (1 - state.demand_cut), min(v.level, Level.HEURISTIC),
                               f"{v.source} x (1 - {state.demand_cut:.3f} stock-out carry-over)") if k[0] == "us" else v)
                    for k, v in demanded.items()}
        notes.append(f"our demand cut by {100 * state.demand_cut:.1f} % for last quarter's stock-outs (heuristic)")
    new.demand_cut = 0.0
    if jit:
        _jit_production(pack, state, plan, new, own_offers, demanded, lines, unit_costs, produced_units, notes)
    revenue: list[Tagged] = []
    sold_total = 0.0
    for offer in own_offers:
        want = demanded.get(("us", offer.brand), Tagged(0.0, demand_level, "no demand"))
        sold = min(want.value, new.inventory.get(offer.brand, 0.0))
        new.inventory[offer.brand] = new.inventory.get(offer.brand, 0.0) - sold
        sold_total += sold
        lines[f"units_demanded[{offer.brand}]"] = want
        sold_level = want.level if offer.brand not in released else min(want.level, released[offer.brand].level)
        if offer.brand in units_level:
            sold_level = min(sold_level, units_level[offer.brand])
        lines[f"units_sold[{offer.brand}]"] = Tagged(sold, sold_level, "min(demand, inventory)")
        revenue.append(Tagged(sold * offer.price, sold_level, "units_sold x price"))
    if not own_offers:
        notes.append("no sales: no priced brand or no open outlet at quarter start")
    rivals_units = sum(v.value for k, v in demanded.items() if k[0] != "us")
    market_units = sold_total + rivals_units
    lines["market_units_total"] = Tagged(market_units, demand_level,
                                         "our units sold + rival units demanded (rivals unconstrained)")
    lines["market_share"] = Tagged(sold_total / market_units if market_units > 0 else 0.0, demand_level,
                                   "our units sold / market_units_total")
    # Per-rival view of the same demand result (report only: no input above changes).
    for firm in sorted({k[0] for k in demanded if k[0] != "us"}):
        firm_units = sum(v.value for k, v in demanded.items() if k[0] == firm)
        lines[f"rival_units[{firm}]"] = Tagged(firm_units, demand_level,
                                               "sum of the rival's units demanded (rivals unconstrained)")
        lines[f"rival_share[{firm}]"] = Tagged(firm_units / market_units if market_units > 0 else 0.0, demand_level,
                                               "rival units / market_units_total")
    # Nothing offered = no revenue (structural zero, independent of the demand model).
    lines["revenue"] = total(revenue, "sum(units_sold x price)", empty_level=demand_level if own_offers else Level.VERIFIED)
    for key, rate in effects.revenue_rates.items():
        lines[key] = Tagged(lines["revenue"].value * rate.value, min(lines["revenue"].level, rate.level),
                            f"revenue x {rate.source}")
    module_income: list[str] = []

    def _held_cost(brand_name: str) -> Tagged:  # this quarter's production cost when made now, else the rule
        return unit_costs.get(brand_name) or _unit_cost(pack, new, brand_name, effects)

    sold_units = {o.brand: lines[f"units_sold[{o.brand}]"].value for o in own_offers}

    def outcome(expense_lines: tuple[str, ...] = (), income_lines: tuple[str, ...] = ()) -> Outcome:
        costs = {b: unit_costs.get(b) or _unit_cost(pack, new, b, effects) for b in new.inventory if b in new.brands}
        return Outcome(lines, sold_units, produced_units, {b: u.value for b, u in released.items()},
                       dict(state.inventory), dict(new.inventory), costs,
                       {"stock_total": new.stock_total, "cd": new.cd, "stock_start": state.stock_total,
                        "cd_start": state.cd, "fixed_capacity_units": state.fixed_capacity_units + plan.capacity_increase},
                       expense_lines, income_lines)

    if effects.modules:  # sales-dependent module expenses and income (rebates paid, warranty, inventory tax)
        for key, late in effects.hook("settle", outcome()):
            effects.merge_late(key, late)
            lines.update(late.lines)
            lines.update(late.expenses)
            lines.update(late.income)
    for key in effects.income:  # module income lines (other income in the game's statement)
        lines[key] = effects.income[key]
        module_income.append(key)
    if released and effects.salvage_fraction is not None:
        frac = effects.salvage_fraction
        parts = [u.scaled(frac.value, frac.source).with_level(frac.level) for u in released.values()]
        value = [Tagged(p.value * _held_cost(b).value, min(p.level, _held_cost(b).level),
                        f"{p.source} x unit cost") for p, b in zip(parts, released, strict=True)]
        lines["inventory_selloff_proceeds"] = total(value, "sold-off units x salvage fraction x unit cost")
        module_income.append("inventory_selloff_proceeds")
    if effects.holding_rate is not None:
        rate = effects.holding_rate
        held = [Tagged(left * _held_cost(b).value * rate.value,
                       min(rate.level, _held_cost(b).level), f"units x unit cost x {rate.source}")
                for b, left in sorted(new.inventory.items()) if left > 0]
        lines["inventory_holding_cost"] = total(held, "ending units x unit cost x quarterly carrying rate",
                                                empty_level=rate.level)

    expense_keys = ("store_setup", "web_center_setup", "outlet_lease", "design_cost", "production_cost", "advertising",
                    *(("factory_excess_capacity_cost",) if jit else ()),
                    *effects.expenses, *effects.revenue_rates,
                    *(("inventory_holding_cost",) if "inventory_holding_cost" in lines else ()))
    expenses = total([lines[k] for k in expense_keys], "operating expenses")
    pretax = lines["revenue"] + lines["cd_interest"] - expenses
    for key in module_income:  # e.g. sell-off proceeds (other income in the game's statement)
        pretax = pretax + lines[key]
    produced = any(new.inventory.get(b, 0.0) > 0 or state.inventory.get(b, 0.0) > 0 for b in new.inventory) or any(
        bp.production > 0 for bp in plan.brands)
    lines["income_tax"] = m.income_tax(pack, pretax, inventory_free=not produced)
    if effects.modules:  # a module may tax on another basis (accrual income with loss carry-forward)
        taxes = [t for _, t in effects.hook("tax", outcome(expense_keys, tuple(module_income))) if t is not None]
        if len(taxes) > 1:
            raise ValueError("two business modules compute the income tax")
        if taxes:
            lines["income_tax"] = taxes[0]
    # Our profit is cash-basis (production expensed when made, no depreciation). The game's income statement is
    # accrual (cost of goods sold, depreciation; captured Q1 structure), so these two lines are a different
    # statement, not just uncalibrated: they never rank above placeholder. Cash below uses the uncapped figures.
    accrual = "cash-basis profit; the game's income statement is accrual (COGS, depreciation): structure differs"
    lines["operating_profit_before_tax"] = pretax.with_level(Level.PLACEHOLDER, f"{pretax.source} [{accrual}]")
    net = pretax - lines["income_tax"]
    lines["net_income"] = net.with_level(Level.PLACEHOLDER, f"{net.source} [{accrual}]")

    cash = (start_cash + lines["revenue"] + lines["stock_raised"] + cd_flow + lines["cd_interest"] - expenses
            - lines["capex_capacity"] - lines["income_tax"])
    for key in module_income:
        cash = cash + lines[key]
    for key, flow in effects.financing.items():  # loans and dividends: cash flows outside profit
        lines[key] = flow
        cash = cash + flow
    loan = m.emergency_loan(cash)
    lines["emergency_loan"] = loan
    lines["cash_end"] = cash + loan
    new.cash = lines["cash_end"].value
    new.cash_level = lines["cash_end"].level.label

    if effects.modules:  # report-only lines once cash is known (balance sheet, scorecard, demand history)
        for key, late in effects.hook("close", outcome(expense_keys, tuple(module_income))):
            effects.merge_late(key, late)
            lines.update(late.lines)
    new.module_state = {**{k: v for k, v in state.module_state.items()
                           if k not in effects.active and k not in effects.stopped}, **effects.state}
    new.fixed_capacity_units = state.fixed_capacity_units + plan.capacity_increase
    new.operating_capacity = float(plan.factory.get("operating_capacity", 0.0)) if jit and plan.factory else 0.0
    new.pending_capacity_units = 0.0
    new.quarter = state.quarter + 1
    lines["fixed_capacity_next_quarter"] = Tagged(state.fixed_capacity_units + plan.capacity_increase, Level.DERIVED,
                                                   "current + increase (screen 'next quarter' row)")
    return new, Report(state.quarter, plan.name, lines, notes)


def _jit_production(pack: ParamPack, state: CompanyState, plan: Plan, new: CompanyState, own_offers: list[m.Offer],
                    demanded: dict[tuple[str, str], Tagged], lines: dict[str, Tagged], unit_costs: dict[str, Tagged],
                    produced_units: dict[str, float], notes: list[str]) -> None:
    """Just-in-time factory (``marketplace_sim.factory``): build what is demanded beyond stock, within operating
    capacity plus authorised overtime; labour and overhead are paid on the scheduled capacity (idle part =
    excess capacity cost); lost sales cut next quarter's demand."""
    from marketplace_sim.factory import DEFAULT_PRODUCTIVITY, BrandOrder, Schedule, run

    spec = plan.factory or {}
    productivity = float(spec.get("productivity") or pack.production.get("workers_productivity") or DEFAULT_PRODUCTIVITY)
    schedule = Schedule(float(spec.get("operating_capacity", 0.0)), float(spec.get("max_overtime_hours", 0.0)),
                        productivity, state.operating_capacity)
    orders, levels = [], []
    for offer in own_offers:
        brand = new.brands[offer.brand]
        want = demanded.get(("us", offer.brand), Tagged(0.0, Level.LITERATURE, "no demand"))
        levels.append(want.level)
        need = max(want.value - new.inventory.get(offer.brand, 0.0), 0.0)
        orders.append(BrandOrder(offer.brand, brand.brand_type, tuple(brand.components), offer.price, need))
    if not orders:
        orders = [BrandOrder(b.name, b.brand_type, tuple(b.components), 0.0, 0.0) for b in new.brands.values()][:1]
    if not orders or not pack.cost_estimates:
        raise ValueError("the factory block needs a brand and a pack with the game's cost table (cost_estimates)")
    reading = str(pack.extras.get("cost_reading", "factory"))
    r = run(pack, orders, schedule, 1.0, reading=reading, fixed_capacity=state.fixed_capacity_units)
    demand_level = min(levels) if levels else Level.VERIFIED
    E, H, D = Level.ESTIMATED, Level.HEURISTIC, Level.DERIVED
    regular_paid = min(r.produced, r.regular_capacity)
    lines["operating_capacity"] = Tagged(schedule.operating_capacity, Level.VERIFIED, "plan input (units/day)")
    lines["capacity_units_per_quarter"] = Tagged(r.regular_capacity, D, "operating capacity x 65 days x productivity")
    lines["max_capacity_with_overtime"] = Tagged(r.max_capacity, D, "with authorised overtime and its fatigue curve")
    lines["overtime_hours_used"] = Tagged(r.overtime_hours_used, demand_level, "smallest overtime that covers demand")
    lines["factory_material_cost"] = Tagged(r.material_cost, min(E, demand_level), "units made x material part of the cost table")
    lines["factory_conversion_used"] = Tagged(r.conversion_per_unit * regular_paid, min(E, demand_level),
                                              "labour + overhead per unit of scheduled capacity x units made in regular time")
    lines["factory_overtime_premium"] = Tagged(r.overtime_premium, min(H, demand_level) if r.overtime_premium else D,
                                       "overtime units x conversion x (labour share x pay change + 1), fatigue-adjusted")
    lines["capacity_change_cost"] = Tagged(r.change_cost, H if r.change_cost else D,
                                           "min increase cost + var increase x added units (screen parameters; formula unverified)")
    production = r.production_cost - r.conversion_per_unit * r.idle_units  # the idle part is the excess-capacity line
    prod_level = min(E, demand_level, *([H] if r.overtime_premium or r.change_cost else []))
    lines["production_cost"] = Tagged(production, prod_level, "just-in-time factory: material + labour/overhead used + "
                                      "overtime premium + capacity change cost")
    lines["factory_excess_capacity_cost"] = Tagged(r.conversion_per_unit * r.idle_units, min(E, demand_level),
                                           "idle scheduled capacity x labour + overhead per unit (help text: idle workers are paid)")
    lines["factory_idle_units"] = Tagged(r.idle_units, demand_level, "regular capacity - units made")
    lines["units_lost_total"] = Tagged(r.lost, demand_level, "demand beyond capacity with authorised overtime")
    shared = (production - r.material_cost) / r.produced if r.produced else 0.0
    for o in orders:
        made = r.made.get(o.name, 0.0)
        produced_units[o.name] = made
        new.inventory[o.name] = new.inventory.get(o.name, 0.0) + made
        cost = Tagged(r.material_by_brand.get(o.name, 0.0) + shared, prod_level,
                      "material part + (labour/overhead used + overtime premium + change cost) / units made")
        lines[f"unit_cost[{o.name}]"] = cost
        unit_costs[o.name] = cost
    new.demand_cut = r.next_quarter_demand_cut
    lines["demand_cut_next_quarter"] = Tagged(r.next_quarter_demand_cut, min(H, demand_level),
                                              "half the unmet share of demand (team's reading of the help file)")
    notes.extend(r.notes)
    if r.lost > 0:
        notes.append(f"stock-out: {r.lost:.0f} units not built; next quarter's demand cut {100 * r.next_quarter_demand_cut:.1f} %")


def _segment(pack: ParamPack, state: CompanyState, bp: BrandPlan) -> str | None:
    """The segment a planned brand targets (carried brand, else the plan, else its type's segment)."""
    if bp.name in state.brands:
        return state.brands[bp.name].segment_id
    return bp.segment or pack.brand_type(bp.brand_type).segment_id


def _unit_cost(pack: ParamPack, state: CompanyState, brand_name: str, effects: Any,
               volume: float | None = None) -> Tagged:
    """Unit cost of a brand this quarter (produced, held or sold off), with the business modules' cost effects."""
    brand = state.brands[brand_name]
    bt = pack.brand_type(brand.brand_type)
    return m.unit_cost(pack, bt, [pack.component(c) for c in brand.components],
                       material_factor=effects.material_cost_factor, labor_factor=effects.labor_cost_factor,
                       conversion_factor=effects.conversion_factor.get(brand_name),
                       add=effects.unit_cost_add.get(brand_name), volume=volume)
