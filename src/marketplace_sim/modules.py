"""Engine modules. Each returns Tagged numbers with an explicit source level.

* VERIFIED: thin wrappers around ``marketplace_sysid.cost_model`` (reproduced against measured server results).
* DERIVED: follows directly from pack parameters (exact identities, display conversions).
* LITERATURE: demand forms with published support and uncalibrated coefficients (``marketplace_sim.demand``).
* PLACEHOLDER: illustrative rules for parts of the economy that are not yet measured.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from marketplace_sim.pack import BrandType, Component, Market, OutletSpec, ParamPack
from marketplace_sim.provenance import Level, Tagged, const, total
from marketplace_sysid import cost_model as cm

V, D, E, L, P = Level.VERIFIED, Level.DERIVED, Level.ESTIMATED, Level.LITERATURE, Level.PLACEHOLDER


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


def income_tax(pack: ParamPack, pretax: Tagged, *, inventory_free: bool = False) -> Tagged:
    """Placeholder tax on our cash-basis profit. The game taxes accrual income after a loss carry-forward and also
    has an inventory tax (captured Q1 statement structure), so the positive branch is unverified and known to be
    incomplete. Structural zero: a cash-basis loss with no production and no inventory means accrual income is not
    higher than ours (no cost of goods held back, depreciation only lowers it), so taxable income <= 0 and no
    inventory can be taxed. That zero is as certain as the sign of pretax."""
    rate = pack.finance.get("tax_rate_percent", 0.0)
    value = max(pretax.value, 0.0) * rate / 100
    if pretax.value <= 0 and inventory_free:
        return Tagged(value, min(pretax.level, V), "no tax: pre-tax loss, nothing produced or held (structural zero; "
                      "the loss row of the captured statement can only lower taxable income)")
    return Tagged(value, P, "max(pretax,0) x taxRate (placeholder: tax rule unverified)")


def emergency_loan(cash_before: Tagged) -> Tagged:
    """Covers negative cash (placeholder; the game charges emergency-loan interest, not modelled). Zero branch:
    with non-negative cash no loan is taken (the captured Q1 statement shows no emergency loan at positive cash)."""
    value = max(-cash_before.value, 0.0)
    if cash_before.value >= 0:
        return Tagged(value, min(cash_before.level, V), "no emergency loan: cash not negative (captured Q1 statement: "
                      "no loan at positive cash; a minimum-cash threshold, if any, is unverified)")
    return Tagged(value, P, "covers negative cash (placeholder: emergency-loan rule unverified)")


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
    value = sum(o.lease_cost for o in outlets if o.key in open_keys)
    if not any(o.key in open_keys for o in outlets):
        # Nothing open at quarter start: an outlet opened this quarter pays no lease (EXP-11/12 measured totalLease 0
        # in the opening quarter), so no timing rule can make this non-zero.
        return Tagged(value, V, "no outlet open at quarter start: no lease (EXP-11/12: none in the opening quarter)")
    return Tagged(value, P, "leaseCost of outlets open at quarter start (placeholder: lease timing unverified)")


# --- product and production ------------------------------------------------------------------------------------------

def compatible(component: Component, brand_type: BrandType) -> bool:
    """A component fits a brand type when their type masks overlap, or when the component has no mask."""
    return bool(component.type_mask & brand_type.type_mask) or not component.type_mask


def default_components(pack: ParamPack, brand_type: BrandType) -> list[Component]:
    chosen = []
    for group in pack.component_groups:
        if not group.required:
            continue
        candidates = [c for c in pack.components if c.group == group.id and compatible(c, brand_type)]
        if candidates:
            chosen.append(min(candidates, key=lambda c: c.price))
    return chosen


def unit_cost(pack: ParamPack, brand_type: BrandType, components: Sequence[Component],
              material_factor: Tagged | None = None) -> Tagged:
    material = sum(c.price for c in components) * brand_type.cost_adj
    labor = pack.production.get("min_direct_labor", 0.0)
    overhead = pack.production.get("min_overhead_cpu", 0.0)
    rule = "sum(component price) x costAdj + minDirectLabor + minOverheadCPU (placeholder: cost function unverified)"
    if material_factor is None:
        return Tagged(material + labor + overhead, P, rule)
    return Tagged(material * material_factor.value + labor + overhead, min(P, material_factor.level),
                  f"{rule}; material x ({material_factor.source})")


def design_cost(pack: ParamPack, new_brands: int) -> Tagged:
    value = new_brands * pack.production.get("design_cost", 0.0)
    if new_brands == 0:
        return Tagged(value, V, "no new brand designed: no design cost (structural zero)")
    return Tagged(value, P, "designCost per new brand (placeholder: when and how the game charges it is unverified)")


# --- demand --------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Offer:
    firm: str
    brand: str
    segment_id: str  # segment the offer targets
    price: float
    fit: float  # PlaceholderDemand only: fit to the targeted segment
    advertising: float  # spend this quarter
    markets: frozenset[str]
    position: str | None = None  # segment the product is designed for (ideal point); defaults to segment_id
    quality: float = 1.0  # 0..1 product quality multiplier on fit (literature demand)
    ad_stock: float | None = None  # goodwill stock; None = steady state of `advertising`
    coverage: tuple[tuple[str, float], ...] = ()  # (market, distribution intensity 0..1); empty = 1 in `markets`
    effort: float = 1.0  # selling-effort multiplier on attraction (business module sales_force; 1 = no module)
    media: tuple[tuple[str, float, float], ...] = ()  # (medium, spend share, elasticity weight); empty = one response

    def coverage_in(self, market: str) -> float:
        if self.coverage:
            return dict(self.coverage).get(market, 0.0)
        return 1.0 if market in self.markets else 0.0


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
                           * (1 + 0.1 * math.log1p(_media_ratio(max(o.advertising, 0) / 1000, o.media))) * o.effort
                           for o in present]
                denominator = 1 + sum(weights)
                for offer, weight in zip(present, weights, strict=True):
                    key = (offer.firm, offer.brand)
                    out[key] = out.get(key, 0.0) + cell.size_12m / 4 * weight / denominator
        return {k: Tagged(v, P, "PlaceholderDemand (uncalibrated logit share)") for k, v in out.items()}


class FittedDemand:
    """Demand fitted on the private demand panel (evidence/private/model/demand_panel): the literature form with
    estimated coefficients. Loads ``model_path`` (schema marketplace-sim/fitted-demand@1) and refuses it unless its
    hold-out validation passes; see docs/demand-model-spec.md section 6. Fitted values never leave evidence/private.
    """

    level = E

    def __init__(self, model_path: str, pack: ParamPack | None = None) -> None:
        self.model_path = model_path
        self.pack = pack
        self._cached: Any = None

    def _model(self) -> Any:
        if self._cached is None:
            from marketplace_sim.demand import LiteratureDemand, load_fitted_coefficients

            model = LiteratureDemand(load_fitted_coefficients(self.model_path), pack=self.pack)
            model.level = E
            model.name = "FittedDemand"
            self._cached = model
        return self._cached

    @property
    def coefficients(self) -> dict[str, Any]:
        coefficients: dict[str, Any] = self._model().coefficients
        return coefficients

    @property
    def carryover(self) -> float:
        return float(self._model().carryover)

    def units(self, pack: ParamPack, offers: Sequence[Offer]) -> dict[tuple[str, str], Tagged]:
        result: dict[tuple[str, str], Tagged] = self._model().units(pack, offers)
        return result


def _media_ratio(ratio: float, media: tuple[tuple[str, float, float], ...]) -> float:
    """Advertising ratio after a media split (business module marketing.media_mix); unchanged without a split."""
    if not media:
        return ratio
    from marketplace_sim.business.marketing import effective_ratio

    return effective_ratio(ratio, media)


def segment_fit(brand_type: BrandType, segment_id: str) -> float:
    return 1.0 if brand_type.segment_id == segment_id else 0.4


def coverage(pack: ParamPack, stores_open: set[str], web_open: set[str], web_weight: float) -> dict[str, float]:
    """Distribution intensity per market: 1 - (1 - store) x (1 - web_weight x web) (docs/demand-model-spec.md)."""
    regions_with_web = {w.region for w in pack.web_centers if w.key in web_open}
    out = {}
    for market in pack.markets:
        store = 1.0 if market.key in stores_open else 0.0
        web = 1.0 if market.region in regions_with_web else 0.0
        intensity = 1.0 - (1.0 - store) * (1.0 - web_weight * web)
        if intensity > 0:
            out[market.key] = intensity
    return out


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
            result.append(Offer(self.name, f"{self.name}-{segment.id}", segment.id, 0.9 * wtp, 1.0, 20000.0, markets,
                                position=segment.id))
        return result


class RandomBot:
    """Random but plausible offers: price 75–105 % of willingness to pay, fit 0.6–1.0, advertising 0–60k."""

    def __init__(self, name: str) -> None:
        self.name = name

    def offers(self, pack: ParamPack, quarter: int, rng: random.Random) -> list[Offer]:
        markets = frozenset(m.key for m in pack.markets if rng.random() < 0.7)
        result = []
        for s in pack.segments:
            price, fit, adv = rng.uniform(0.75, 1.05) * _mean_wtp(pack.markets, s.id), rng.uniform(0.6, 1.0), rng.uniform(0, 60000)
            result.append(Offer(self.name, f"{self.name}-{s.id}", s.id, price, fit, adv, markets, position=s.id, quality=fit))
        return result


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
           "capacity_purchase", "cd_quarter", "compatible", "const", "coverage", "default_components", "design_cost", "emergency_loan",
           "income_tax", "opening_cost", "quarterly_capacity", "reach", "recurring_lease", "segment_fit", "stock_raise",
           "total", "unit_cost"]
