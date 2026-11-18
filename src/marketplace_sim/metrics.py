"""Registry behind ``mpsim explain``: how each report line is computed, its level, and where the evidence is."""

from __future__ import annotations

from dataclasses import dataclass

from marketplace_sim.provenance import Level


@dataclass(frozen=True)
class MetricInfo:
    name: str
    level: Level
    formula: str
    evidence: str
    note: str = ""
    inputs: tuple[str, ...] = ()  # report lines this metric is computed from (for the source chain)


METRICS: dict[str, MetricInfo] = {m.name: m for m in [
    MetricInfo("cash_start", Level.VERIFIED, "state.cash", "save file"),
    MetricInfo("capex_capacity", Level.VERIFIED, "cost of the chosen capacity option row", "docs/experiments/EXP-02.md"),
    MetricInfo("capacity_units_per_quarter", Level.VERIFIED, "fixed capacity (units/day) x days per quarter",
               "docs/experiments/EXP-02.md; docs/calculation-map.md #3"),
    MetricInfo("store_setup", Level.VERIFIED, "sum(setup_cost) of stores opened this quarter",
               "docs/experiments/EXP-11-OpenSalesOffice.md"),
    MetricInfo("web_center_setup", Level.VERIFIED, "sum(setup_cost) of web centers opened this quarter",
               "docs/experiments/EXP-12-OpenWebcenter.md"),
    MetricInfo("outlet_lease", Level.PLACEHOLDER, "lease_cost of outlets open at quarter start",
               "docs/decisions-log.md #151",
               "Candidate: full lease in the quarter after opening reproduces the game's projected cash (one quarter)."),
    MetricInfo("cd_balance", Level.VERIFIED, "cd_prior + deposit - withdraw", "docs/experiments/EXP-01.md",
               "Only the deposit term was varied in the experiment."),
    MetricInfo("cd_interest", Level.VERIFIED, "cd_balance x annual rate / 4 / 100", "docs/experiments/EXP-01.md"),
    MetricInfo("stock_raised", Level.DERIVED, "sum(shares x price)", "docs/calculate-screen-triage.md (Stock, view identity)"),
    MetricInfo("unit_cost[brand]", Level.PLACEHOLDER,
               "game cost table at the volume (estimated) when the pack has one; else sum(component price) x cost_adj "
               "+ min direct labor + min overhead (placeholder)", "src/marketplace_sim/cost_curve.py; docs/decisions-log.md #147",
               "Just-in-time factory: material part + labour/overhead used + overtime premium + change cost per unit."),
    MetricInfo("design_cost", Level.PLACEHOLDER, "design_cost x new brands", "docs/decisions-log.md #148",
               "Candidate: charged in the design quarter in the R&D row (Q1 statement reproduced)."),
    MetricInfo("production_cost", Level.PLACEHOLDER, "sum(units x unit_cost)", "see unit_cost"),
    MetricInfo("advertising", Level.VERIFIED, "plan input (spend as entered)", "plan file"),
    MetricInfo("units_demanded[brand]", Level.LITERATURE,
               "sum over city x segment of potential x attraction / (outside + sum attraction)",
               "docs/demand-model-spec.md; docs/demand-literature.md",
               "Literature form, uncalibrated coefficients. Becomes ESTIMATED once FittedDemand passes validation."),
    MetricInfo("units_sold[brand]", Level.LITERATURE, "min(units_demanded, inventory)", "docs/demand-model-spec.md",
               "Takes the demand model's level (placeholder if PlaceholderDemand is selected)."),
    MetricInfo("market_units_total", Level.LITERATURE, "our units sold + rival units demanded",
               "docs/demand-model-spec.md", "Rivals are assumed unconstrained by inventory."),
    MetricInfo("market_share", Level.LITERATURE, "our units sold / market_units_total", "docs/demand-model-spec.md"),
    MetricInfo("rival_units[firm]", Level.LITERATURE, "sum of one rival's units demanded", "docs/demand-model-spec.md",
               "Same demand model as ours; rivals are assumed unconstrained by inventory."),
    MetricInfo("rival_share[firm]", Level.LITERATURE, "rival units / market_units_total", "docs/demand-model-spec.md"),
    MetricInfo("revenue", Level.LITERATURE, "sum(units_sold x price)", "weakest input decides (demand model level)"),
    MetricInfo("operating_profit_before_tax", Level.PLACEHOLDER, "revenue + cd_interest - operating expenses",
               "weakest input decides"),
    MetricInfo("income_tax", Level.PLACEHOLDER, "max(pretax, 0) x tax rate", "rate from pack; rule unverified"),
    MetricInfo("net_income", Level.PLACEHOLDER, "pretax - income_tax", "weakest input decides"),
    MetricInfo("emergency_loan", Level.PLACEHOLDER, "amount needed to bring cash to zero", "rule unverified"),
    MetricInfo("cash_end", Level.PLACEHOLDER, "cash_start + inflows - outflows + emergency_loan",
               "VERIFIED only if every component is"),
    MetricInfo("fixed_capacity_next_quarter", Level.DERIVED, "current + increase", "capacity screen 'next quarter' row"),
    # business modules (marketplace_sim.business): HEURISTIC practice rules, see docs/modeling-ledger.md
    MetricInfo("media_mix_index[brand]", Level.LITERATURE, "Prod_m (1 + s_m / w_m)^w_m / 2 (1 = best split)",
               "src/marketplace_sim/business/marketing.py; docs/demand-literature.md (MCI)",
               "Per-medium MCI advertising terms; media weights are a neutral labelled default."),
    MetricInfo("sales_force_headcount", Level.LITERATURE, "plan input (heuristic when carried after quits)",
               "src/marketplace_sim/business/sales_force.py"),
    MetricInfo("sales_force_hires", Level.LITERATURE, "max(headcount - carried headcount, 0)",
               "src/marketplace_sim/business/sales_force.py"),
    MetricInfo("sales_force_skill", Level.HEURISTIC, "training stock with decay, 0..1",
               "src/marketplace_sim/business/sales_force.py", "Practice rule: no literature, no calibration."),
    MetricInfo("selling_effort", Level.LITERATURE, "(1 + force per market / reference)^selling elasticity",
               "src/marketplace_sim/business/sales_force.py; data/module_defaults.json",
               "Multiplies the attraction of our offers. Heuristic when trained skill or carried headcount is used."),
    MetricInfo("sales_force_quit_rate", Level.HEURISTIC, "base quit x exp(-sensitivity x (pay index - 1)), bounded",
               "src/marketplace_sim/business/sales_force.py", "Practice rule: no literature, no calibration."),
    MetricInfo("sales_force_departures", Level.HEURISTIC, "headcount x quit rate",
               "src/marketplace_sim/business/sales_force.py"),
    MetricInfo("sales_force_salaries", Level.HEURISTIC, "headcount x salary", "src/marketplace_sim/business/sales_force.py"),
    MetricInfo("sales_force_hiring", Level.HEURISTIC, "hires x hire cost + layoffs x severance",
               "src/marketplace_sim/business/sales_force.py"),
    MetricInfo("sales_force_training", Level.HEURISTIC, "headcount x training per person",
               "src/marketplace_sim/business/sales_force.py"),
    MetricInfo("sales_force_commission", Level.HEURISTIC, "revenue x commission %",
               "src/marketplace_sim/business/sales_force.py"),
    MetricInfo("web_sales_headcount", Level.HEURISTIC, "web salespeople (plan input or carried)",
               "src/marketplace_sim/business/sales_force.py"),
    MetricInfo("web_sales_effort", Level.HEURISTIC, "1 + web share x ((1 + web force / reference)^elasticity - 1)",
               "src/marketplace_sim/business/sales_force.py", "Practice rule: no published web-selling elasticity."),
    MetricInfo("web_sales_salaries", Level.HEURISTIC, "web salespeople x salary", "src/marketplace_sim/business/sales_force.py"),
    MetricInfo("inventory_holding_cost", Level.LITERATURE, "ending units x unit cost x annual carrying rate / 4",
               "src/marketplace_sim/business/inventory.py; data/module_defaults.json",
               "Rate in the published range; takes the unit cost's level (placeholder) downstream."),
    MetricInfo("inventory_selloff_units[brand]", Level.HEURISTIC, "plan input: units sold off at quarter start",
               "src/marketplace_sim/business/inventory.py"),
    MetricInfo("inventory_selloff_proceeds", Level.HEURISTIC, "sold-off units x salvage fraction x unit cost",
               "src/marketplace_sim/business/inventory.py", "Salvage fraction is a labelled practice default."),
    MetricInfo("purchasing_discount", Level.HEURISTIC, "all-units discount tier of the contract volume",
               "src/marketplace_sim/business/purchasing.py", "Form: Dolan 1987; tiers are labelled defaults."),
    MetricInfo("material_cost_factor", Level.HEURISTIC, "1 - discount x covered share of production",
               "src/marketplace_sim/business/purchasing.py"),
    MetricInfo("purchasing_shortfall_fee", Level.HEURISTIC, "unproduced contract units x fee",
               "src/marketplace_sim/business/purchasing.py"),
    # just-in-time factory (plan 'factory' block): src/marketplace_sim/factory.py, docs/decisions-log.md #152-153
    MetricInfo("operating_capacity", Level.VERIFIED, "plan input (units/day)", "plan file"),
    MetricInfo("max_capacity_with_overtime", Level.DERIVED,
               "operating capacity x 65 x (1 + overtime/8) x fatigue-adjusted productivity, at most 1.5 x fixed",
               "game help text (Overtime); Overtime screen curve"),
    MetricInfo("overtime_hours_used", Level.LITERATURE, "smallest daily overtime that covers demand",
               "game help text (Rules for Overtime Use)", "Takes the demand level."),
    MetricInfo("factory_material_cost", Level.ESTIMATED, "units made x material part of the game's cost table",
               "src/marketplace_sim/cost_curve.py"),
    MetricInfo("factory_conversion_used", Level.ESTIMATED, "labour + overhead per unit of scheduled capacity x units made",
               "src/marketplace_sim/factory.py"),
    MetricInfo("factory_overtime_premium", Level.HEURISTIC, "overtime units x conversion x (labour share x pay change + 1)",
               "src/marketplace_sim/factory.py", "Labour share is a labelled reading of the screen graph."),
    MetricInfo("capacity_change_cost", Level.HEURISTIC, "min increase cost + var increase x added units per quarter",
               "OperatingCapacity screen parameters", "Formula unverified; the screen shows the figure."),
    MetricInfo("factory_excess_capacity_cost", Level.ESTIMATED, "idle scheduled capacity x labour + overhead per unit",
               "game help text (idle workers are paid); src/marketplace_sim/factory.py"),
    MetricInfo("factory_idle_units", Level.LITERATURE, "regular capacity - units made", "src/marketplace_sim/factory.py"),
    MetricInfo("units_lost_total", Level.LITERATURE, "demand beyond capacity with authorised overtime",
               "src/marketplace_sim/factory.py"),
    MetricInfo("demand_cut_next_quarter", Level.HEURISTIC, "half the unmet share of demand",
               "team's reading of the game help file (stock-outs)", "Applied to our demand next quarter."),
]}


_MODULE_OPEX = ("sales_force_salaries", "sales_force_hiring", "sales_force_training", "sales_force_commission", "web_sales_salaries",
                "inventory_holding_cost", "purchasing_shortfall_fee")
_OPEX = ("store_setup", "web_center_setup", "outlet_lease", "design_cost", "production_cost", "advertising", *_MODULE_OPEX)
INPUTS: dict[str, tuple[str, ...]] = {
    "units_demanded[brand]": ("advertising", "media_mix_index[brand]", "selling_effort"),
    "unit_cost[brand]": ("material_cost_factor",),
    "material_cost_factor": ("purchasing_discount",),
    "inventory_holding_cost": ("unit_cost[brand]",),
    "inventory_selloff_proceeds": ("inventory_selloff_units[brand]", "unit_cost[brand]"),
    "selling_effort": ("sales_force_headcount", "sales_force_skill", "web_sales_effort"),
    "web_sales_effort": ("web_sales_headcount",),
    "web_sales_salaries": ("web_sales_headcount",),
    "sales_force_departures": ("sales_force_headcount", "sales_force_quit_rate"),
    "sales_force_salaries": ("sales_force_headcount",),
    "sales_force_hiring": ("sales_force_hires",),
    "sales_force_training": ("sales_force_headcount",),
    "sales_force_commission": ("revenue",),
    "cd_interest": ("cd_balance",),
    "production_cost": ("unit_cost[brand]",),
    "units_sold[brand]": ("units_demanded[brand]",),
    "market_units_total": ("units_sold[brand]",),
    "market_share": ("units_sold[brand]", "market_units_total"),
    "rival_share[firm]": ("rival_units[firm]", "market_units_total"),
    "revenue": ("units_sold[brand]",),
    "operating_profit_before_tax": ("revenue", "cd_interest", *_OPEX),
    "income_tax": ("operating_profit_before_tax",),
    "net_income": ("operating_profit_before_tax", "income_tax"),
    "emergency_loan": ("cash_start", "revenue", "stock_raised", "cd_interest", "capex_capacity", "income_tax", *_OPEX),
    "cash_end": ("cash_start", "revenue", "stock_raised", "cd_interest", "capex_capacity", "income_tax",
                 "emergency_loan", *_OPEX),
    "fixed_capacity_next_quarter": ("capacity_units_per_quarter",),
}
METRICS = {k: (MetricInfo(v.name, v.level, v.formula, v.evidence, v.note, INPUTS.get(k, ()))) for k, v in METRICS.items()}


def _with_module_metrics() -> tuple[dict[str, MetricInfo], frozenset[str]]:
    """Add the lines declared by the business-module implementations (``metrics`` class attribute), and list each in
    the chains of the core line its role feeds (profit and cash, units, unit cost, capacity, production)."""
    from marketplace_sim.business.registry import IMPLEMENTATIONS

    feeds = {"expense": ("operating_profit_before_tax", "cash_end", "emergency_loan"),
             "income": ("operating_profit_before_tax", "cash_end", "emergency_loan"),
             "financing": ("cash_end", "emergency_loan"), "demand": ("units_demanded[brand]",),
             "cost": ("unit_cost[brand]",), "capacity": ("capacity_units_per_quarter",),
             "plan": ("production_cost",), "tax": ("income_tax",)}
    out = dict(METRICS)
    extra: dict[str, list[str]] = {}
    names: set[str] = set()
    for cls in IMPLEMENTATIONS.values():
        evidence = getattr(cls.spec, "evidence", "")
        for m in getattr(cls, "metrics", ()):
            if m.name in out:
                continue
            out[m.name] = MetricInfo(m.name, m.level, m.formula, evidence, m.note, m.inputs)
            names.add(m.name.split("[", 1)[0])
            for core in feeds.get(m.role, ()):
                extra.setdefault(core, []).append(m.name)
    for core, more in extra.items():
        info = out[core]
        out[core] = MetricInfo(info.name, info.level, info.formula, info.evidence, info.note, (*info.inputs, *more))
    return out, frozenset(names)


METRICS, MODULE_METRICS = _with_module_metrics()


def chain(name: str, present: set[str] | None = None) -> list[MetricInfo]:
    """The metric and everything upstream of it (depth-first, each once): the full source chain of a report line.

    ``present``: base names of the lines in the same report. Upstream metrics absent from it are skipped, so an
    inactive business module never shows up in a chain.
    """
    out: list[MetricInfo] = []
    seen: set[str] = set()

    def walk(metric: str) -> None:
        info = lookup(metric)
        if info is None or info.name in seen:
            return
        base = info.name.split("[", 1)[0]
        if present is not None and out and base not in present:
            return
        if present is None and out and base in MODULE_METRICS:  # no report: a module's lines only when it runs
            return
        seen.add(info.name)
        out.append(info)
        for upstream in info.inputs:
            walk(upstream)

    walk(name)
    return out


def lookup(name: str) -> MetricInfo | None:
    if name in METRICS:
        return METRICS[name]
    base = name.split("[", 1)[0]
    return next((info for key, info in METRICS.items() if key.split("[", 1)[0] == base), None)
