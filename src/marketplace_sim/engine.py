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
    effects = run_modules(pack, quarter=state.quarter, decisions=plan.modules, carried=state.module_state,
                          brands=[BrandInput(bp.name, bp.advertising, bp.production, bp.price) for bp in plan.brands],
                          markets_reached=len(market_reach), inventory=state.inventory)
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
    for bp in plan.brands:
        bt = pack.brand_type(bp.brand_type)
        if bp.name not in new.brands:
            comps = [pack.component(c) for c in bp.components] if bp.components else m.default_components(pack, bt)
            new.brands[bp.name] = Brand(bp.name, bt.code, [c.id for c in comps], bp.segment or bt.segment_id)
            new_brand_count += 1
        brand = new.brands[bp.name]
        cost = m.unit_cost(pack, bt, [pack.component(c) for c in brand.components],
                           material_factor=effects.material_cost_factor)
        lines[f"unit_cost[{bp.name}]"] = cost
        units = min(bp.production, capacity_left)
        if units < bp.production:
            notes.append(f"{bp.name}: production capped by capacity ({units:.0f} of {bp.production:.0f})")
        capacity_left -= units
        new.inventory[bp.name] = new.inventory.get(bp.name, 0.0) + units
        if units > 0:  # nothing produced costs nothing, whatever the (unverified) unit-cost rule says
            production_cost.append(cost.scaled(units, f"{units:.0f} units"))
        segment = brand.segment_id or (pack.segments[0].id if pack.segments else "")
        stock = carryover * state.ad_stock.get(bp.name, 0.0) + max(bp.advertising, 0.0)
        new.ad_stock[bp.name] = stock
        split = effects.media_split.get(bp.name)
        if bp.price > 0 and market_reach:
            own_offers.append(m.Offer("us", bp.name, segment, bp.price, m.segment_fit(bt, segment), bp.advertising,
                                      market_reach, position=bt.segment_id, quality=1.0, ad_stock=stock,
                                      coverage=market_coverage, effort=effort, media=split.parts if split else ()))
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
    revenue: list[Tagged] = []
    sold_total = 0.0
    for offer in own_offers:
        want = demanded.get(("us", offer.brand), Tagged(0.0, demand_level, "no demand"))
        sold = min(want.value, new.inventory.get(offer.brand, 0.0))
        new.inventory[offer.brand] = new.inventory.get(offer.brand, 0.0) - sold
        sold_total += sold
        lines[f"units_demanded[{offer.brand}]"] = want
        sold_level = want.level if offer.brand not in released else min(want.level, released[offer.brand].level)
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
    if released and effects.salvage_fraction is not None:
        frac = effects.salvage_fraction
        parts = [u.scaled(frac.value, frac.source).with_level(frac.level) for u in released.values()]
        value = [Tagged(p.value * _unit_cost(pack, new, b, effects).value, min(p.level, _unit_cost(pack, new, b, effects).level),
                        f"{p.source} x unit cost") for p, b in zip(parts, released, strict=True)]
        lines["inventory_selloff_proceeds"] = total(value, "sold-off units x salvage fraction x unit cost")
        module_income.append("inventory_selloff_proceeds")
    if effects.holding_rate is not None:
        rate = effects.holding_rate
        held = [Tagged(left * _unit_cost(pack, new, b, effects).value * rate.value,
                       min(rate.level, _unit_cost(pack, new, b, effects).level), f"units x unit cost x {rate.source}")
                for b, left in sorted(new.inventory.items()) if left > 0]
        lines["inventory_holding_cost"] = total(held, "ending units x unit cost x quarterly carrying rate",
                                                empty_level=rate.level)

    expenses = total([lines["store_setup"], lines["web_center_setup"], lines["outlet_lease"], lines["design_cost"],
                      lines["production_cost"], lines["advertising"],
                      *(lines[k] for k in [*effects.expenses, *effects.revenue_rates]),
                      *([lines["inventory_holding_cost"]] if "inventory_holding_cost" in lines else [])],
                     "operating expenses")
    pretax = lines["revenue"] + lines["cd_interest"] - expenses
    for key in module_income:  # e.g. sell-off proceeds (other income in the game's statement)
        pretax = pretax + lines[key]
    produced = any(new.inventory.get(b, 0.0) > 0 or state.inventory.get(b, 0.0) > 0 for b in new.inventory) or any(
        bp.production > 0 for bp in plan.brands)
    lines["income_tax"] = m.income_tax(pack, pretax, inventory_free=not produced)
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
    loan = m.emergency_loan(cash)
    lines["emergency_loan"] = loan
    lines["cash_end"] = cash + loan
    new.cash = lines["cash_end"].value
    new.cash_level = lines["cash_end"].level.label

    new.module_state = {**{k: v for k, v in state.module_state.items() if k not in effects.active}, **effects.state}
    new.fixed_capacity_units = state.fixed_capacity_units + plan.capacity_increase
    new.pending_capacity_units = 0.0
    new.quarter = state.quarter + 1
    lines["fixed_capacity_next_quarter"] = Tagged(state.fixed_capacity_units + plan.capacity_increase, Level.DERIVED,
                                                   "current + increase (screen 'next quarter' row)")
    return new, Report(state.quarter, plan.name, lines, notes)


def _unit_cost(pack: ParamPack, state: CompanyState, brand_name: str, effects: Any) -> Tagged:
    """Unit cost of a carried brand (for valuing inventory held or sold off), with this quarter's material factor."""
    brand = state.brands[brand_name]
    bt = pack.brand_type(brand.brand_type)
    return m.unit_cost(pack, bt, [pack.component(c) for c in brand.components],
                       material_factor=effects.material_cost_factor)
