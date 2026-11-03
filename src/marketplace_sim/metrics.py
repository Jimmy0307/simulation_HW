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
               "docs/cost-model.md (not covered)", "Lease timing after opening is unverified."),
    MetricInfo("cd_balance", Level.VERIFIED, "cd_prior + deposit - withdraw", "docs/experiments/EXP-01.md",
               "Only the deposit term was varied in the experiment."),
    MetricInfo("cd_interest", Level.VERIFIED, "cd_balance x annual rate / 4 / 100", "docs/experiments/EXP-01.md"),
    MetricInfo("stock_raised", Level.DERIVED, "sum(shares x price)", "docs/calculate-screen-triage.md (Stock, view identity)"),
    MetricInfo("unit_cost[brand]", Level.PLACEHOLDER, "sum(component price) x cost_adj + min direct labor + min overhead",
               "docs/cost-model.md (not covered)", "The real production cost function is not yet measured."),
    MetricInfo("design_cost", Level.PLACEHOLDER, "design_cost x new brands", "pack parameter; charging rule unverified"),
    MetricInfo("production_cost", Level.PLACEHOLDER, "sum(units x unit_cost)", "see unit_cost"),
    MetricInfo("advertising", Level.VERIFIED, "plan input (spend as entered)", "plan file"),
    MetricInfo("units_sold[brand]", Level.PLACEHOLDER, "min(demand, inventory) with PlaceholderDemand",
               "src/marketplace_sim/modules.py", "Becomes ESTIMATED once FittedDemand is calibrated."),
    MetricInfo("revenue", Level.PLACEHOLDER, "sum(units_sold x price)", "depends on demand model"),
    MetricInfo("operating_profit_before_tax", Level.PLACEHOLDER, "revenue + cd_interest - operating expenses",
               "weakest input decides"),
    MetricInfo("income_tax", Level.PLACEHOLDER, "max(pretax, 0) x tax rate", "rate from pack; rule unverified"),
    MetricInfo("net_income", Level.PLACEHOLDER, "pretax - income_tax", "weakest input decides"),
    MetricInfo("emergency_loan", Level.PLACEHOLDER, "amount needed to bring cash to zero", "rule unverified"),
    MetricInfo("cash_end", Level.PLACEHOLDER, "cash_start + inflows - outflows + emergency_loan",
               "VERIFIED only if every component is"),
    MetricInfo("fixed_capacity_next_quarter", Level.DERIVED, "current + increase", "capacity screen 'next quarter' row"),
]}


def lookup(name: str) -> MetricInfo | None:
    if name in METRICS:
        return METRICS[name]
    base = name.split("[", 1)[0]
    return next((info for key, info in METRICS.items() if key.split("[", 1)[0] == base), None)
