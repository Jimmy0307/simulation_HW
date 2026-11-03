"""Engine modules. Each returns Tagged numbers with an explicit source level.

* VERIFIED: thin wrappers around ``marketplace_sysid.cost_model`` (reproduced against measured server results).
* DERIVED: follows directly from pack parameters (exact identities, display conversions).
* PLACEHOLDER: illustrative rules for parts of the economy that are not yet measured.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from marketplace_sim.pack import BrandType, Component, Market, OutletSpec, ParamPack
from marketplace_sim.provenance import Level, Tagged, const, total
from marketplace_sysid import cost_model as cm

V, D, E, P = Level.VERIFIED, Level.DERIVED, Level.ESTIMATED, Level.PLACEHOLDER


# --- finance -----------------------------------------------------------------------------------------------------

def cd_quarter(pack: ParamPack, cd_prior: float, deposit: float, withdraw: float) -> tuple[Tagged, Tagged]:
    result = cm.cd_projection(deposit, withdraw, cd_prior=cd_prior,
                              rate_annual_percent=pack.finance["cd_rate_annual_percent"])
    return (Tagged(result.cd, V, "cd = cd_prior + deposit - withdraw (EXP-01)"),
            Tagged(result.interest, V, "interest = cd x rate/4/100 (EXP-01)"))


def stock_raise(issues: Iterable[tuple[float, float]], stock_prior: float, shares_prior: float) -> tuple[Tagged, Tagged]:
    result = cm.stock_issue([cm.StockIssue(s, p) for s, p in issues], stock_total_prior=stock_prior,
                            shares_total_prior=shares_prior)
    return (Tagged(result.stock_increase, D, "sum(shares x price) (view identity)"),
            Tagged(result.shares_increase, D, "sum(shares) (view identity)"))


def income_tax(pack: ParamPack, pretax: Tagged) -> Tagged:
    rate = pack.finance.get("tax_rate_percent", 0.0)
    return Tagged(max(pretax.value, 0.0) * rate / 100, P, "max(pretax,0) x taxRate (placeholder: tax rule unverified)")


def emergency_loan(cash_before: Tagged) -> Tagged:
    return Tagged(max(-cash_before.value, 0.0), P, "covers negative cash (placeholder: emergency-loan rule unverified)")


# --- capacity ------------------------------------------------------------------------------------------------------

def capacity_purchase(pack: ParamPack, increase_units: float) -> Tagged:
    options = [cm.CapacityOption(o.units, o.cost, o.machines) for o in pack.capacity_options]
    return Tagged(cm.capacity_investment(increase_units, options).total, V, "capacity option cost (EXP-02)")


def quarterly_capacity(pack: ParamPack, units_per_day: float) -> Tagged:
    return Tagged(units_per_day * pack.days_per_quarter, V, f"units/day x {pack.days_per_quarter} (EXP-02 + client)")


# --- outlets -------------------------------------------------------------------------------------------------------

def opening_cost(outlets: Sequence[OutletSpec], open_now: Iterable[str], already_open: set[str], what: str) -> Tagged:
    specs = [cm.Outlet(o.key, o.key in already_open, o.setup_cost, o.lease_cost) for o in outlets]
    requested = {key: True for key in open_now if key not in already_open}
    result = cm.store_opening_cost(specs, requested)
    return Tagged(result.total, V, f"sum(setupCost of newly opened {what}) (EXP-11/EXP-12)")


def recurring_lease(outlets: Sequence[OutletSpec], open_keys: set[str]) -> Tagged:
    return Tagged(sum(o.lease_cost for o in outlets if o.key in open_keys), P,
                  "leaseCost of outlets open at quarter start (placeholder: lease timing unverified)")


# --- product and production ------------------------------------------------------------------------------------------

def default_components(pack: ParamPack, brand_type: BrandType) -> list[Component]:
    chosen = []
    for group in pack.component_groups:
        if not group.required:
            continue
        candidates = [c for c in pack.components if c.group == group.id and (c.type_mask & brand_type.type_mask or not c.type_mask)]
        if candidates:
            chosen.append(min(candidates, key=lambda c: c.price))
    return chosen


def unit_cost(pack: ParamPack, brand_type: BrandType, components: Sequence[Component]) -> Tagged:
    material = sum(c.price for c in components) * brand_type.cost_adj
    labor = pack.production.get("min_direct_labor", 0.0)
    overhead = pack.production.get("min_overhead_cpu", 0.0)
    return Tagged(material + labor + overhead, P,
                  "sum(component price) x costAdj + minDirectLabor + minOverheadCPU (placeholder: cost function unverified)")


def design_cost(pack: ParamPack, new_brands: int) -> Tagged:
    return Tagged(new_brands * pack.production.get("design_cost", 0.0), P, "designCost per new brand (placeholder)")


# --- demand --------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Offer:
    firm: str
    brand: str
    segment_id: str
    price: float
    fit: float
    advertising: float
    markets: frozenset[str]


class DemandModel(Protocol):
    level: Level

    def units(self, pack: ParamPack, offers: Sequence[Offer]) -> dict[tuple[str, str], Tagged]:
        """Return units demanded per (firm, brand) for one quarter."""


class PlaceholderDemand:
    """Illustrative multinomial-logit share of quarterly segment potential. NOT calibrated.

    attractiveness = fit x exp(3 x (wtp - price)/wtp) x (1 + 0.1 x ln(1 + advertising/1000)); an outside option of
    weight 1 keeps shares below 1. Potential = size_12m / 4 per market and segment, only in markets an offer reaches.
    """

    level = P

    def units(self, pack: ParamPack, offers: Sequence[Offer]) -> dict[tuple[str, str], Tagged]:
        out: dict[tuple[str, str], float] = {}
        for market in pack.markets:
            for segment_id, cell in market.segments.items():
                present = [o for o in offers if o.segment_id == segment_id and market.key in o.markets]
                if not present or cell.wtp <= 0:
                    continue
                weights = [o.fit * math.exp(3 * (cell.wtp - o.price) / cell.wtp)
                           * (1 + 0.1 * math.log1p(max(o.advertising, 0) / 1000)) for o in present]
                denominator = 1 + sum(weights)
                for offer, weight in zip(present, weights, strict=True):
                    key = (offer.firm, offer.brand)
                    out[key] = out.get(key, 0.0) + cell.size_12m / 4 * weight / denominator
        return {k: Tagged(v, P, "PlaceholderDemand (uncalibrated logit share)") for k, v in out.items()}


class FittedDemand:
    """Interface for a demand model fitted on the private demand panel (evidence/private/model/demand_panel).

    Not implemented until at least three quarters of panel data exist; see docs/quarterly-runbook.md.
    """

    level = E

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path

    def units(self, pack: ParamPack, offers: Sequence[Offer]) -> dict[tuple[str, str], Tagged]:
        raise NotImplementedError("FittedDemand needs a fitted model from the private demand panel")


def segment_fit(brand_type: BrandType, segment_id: str) -> float:
    return 1.0 if brand_type.segment_id == segment_id else 0.4


def reach(pack: ParamPack, stores_open: set[str], web_open: set[str]) -> frozenset[str]:
    """Markets an offer can sell in: cities with an open store, plus every city of a region with a web center."""
    regions_with_web = {w.region for w in pack.web_centers if w.key in web_open}
    return frozenset(m.key for m in pack.markets if m.key in stores_open or m.region in regions_with_web)


# --- competitors -----------------------------------------------------------------------------------------------------

class Competitor(Protocol):
    def offers(self, pack: ParamPack, quarter: int, rng: random.Random) -> list[Offer]:
        """Competitor offers for one quarter."""


class BaselineBot:
    """Keeps one constant offer per segment at 90 % of the average willingness to pay."""

    def __init__(self, name: str) -> None:
        self.name = name

    def offers(self, pack: ParamPack, quarter: int, rng: random.Random) -> list[Offer]:
        markets = frozenset(m.key for m in pack.markets)
        result = []
        for segment in pack.segments:
            wtp = _mean_wtp(pack.markets, segment.id)
            result.append(Offer(self.name, f"{self.name}-{segment.id}", segment.id, 0.9 * wtp, 1.0, 20000.0, markets))
        return result


class RandomBot:
    """Random but plausible offers: price 75–105 % of willingness to pay, fit 0.6–1.0, advertising 0–60k."""

    def __init__(self, name: str) -> None:
        self.name = name

    def offers(self, pack: ParamPack, quarter: int, rng: random.Random) -> list[Offer]:
        markets = frozenset(m.key for m in pack.markets if rng.random() < 0.7)
        return [Offer(self.name, f"{self.name}-{s.id}", s.id, rng.uniform(0.75, 1.05) * _mean_wtp(pack.markets, s.id),
                      rng.uniform(0.6, 1.0), rng.uniform(0, 60000), markets) for s in pack.segments]


class ReplayCompetitors:
    """Replays real competitor offers from the private demand panel (one JSON file per quarter)."""

    def __init__(self, panel: Mapping[int, Sequence[Offer]]) -> None:
        self.panel = panel

    def offers(self, pack: ParamPack, quarter: int, rng: random.Random) -> list[Offer]:
        if quarter not in self.panel:
            raise KeyError(f"no recorded competitor offers for quarter {quarter}")
        return list(self.panel[quarter])


def _mean_wtp(markets: Sequence[Market], segment_id: str) -> float:
    values = [m.segments[segment_id].wtp for m in markets if segment_id in m.segments]
    return sum(values) / len(values) if values else 0.0


__all__ = ["BaselineBot", "DemandModel", "FittedDemand", "Offer", "PlaceholderDemand", "RandomBot", "ReplayCompetitors",
           "capacity_purchase", "cd_quarter", "const", "default_components", "design_cost", "emergency_loan",
           "income_tax", "opening_cost", "quarterly_capacity", "reach", "recurring_lease", "segment_fit", "stock_raise",
           "total", "unit_cost"]
