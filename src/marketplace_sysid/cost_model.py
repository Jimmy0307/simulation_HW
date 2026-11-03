"""Cost-side model of Marketplace Simulation, limited to relations verified against the server.

Each function reproduces one server ``calculate`` output (or exact ``view`` identity) from decision inputs plus
parameters published in the screen's own ``view`` response (see ``data/parameter_catalog.json``). Provenance:

=========================  ==========================================  ======================
function                   server output                               evidence
=========================  ==========================================  ======================
``cd_projection``          ``CD.calculate.{cd, interest}``             EXP-01 (2 valid points)
``capacity_investment``    ``FixedCapacity.calculate.{expansion,       EXP-02 (9 points)
                           acquirement, total}``
``quarterly_units``        client display ``units/day × 65``           EXP-02 + client code
``store_opening_cost``     ``OpenSalesOffice.calculate.{totalSetup,    EXP-11 (8 points)
                           totalLease, totalClose, total}``
``web_center_opening_cost``  ``OpenWebcenter.calculate.{...}``          EXP-12 (2 points)
``stock_issue``            ``Stock.calculate.{stockIncrease,           view identity (1 point)
                           sharesIncrease, stockTotal, sharesTotal}``
=========================  ==========================================  ======================

Not modelled (unverified): closing costs and recurring lease of already-opened stores, factory setup, production
cost, taxes, interest on loans, emergency loans, demand. See ``docs/cost-model.md``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

DAYS_PER_QUARTER = 65


@dataclass(frozen=True)
class CDResult:
    cd: float
    interest: float


def cd_projection(deposit: float, withdraw: float = 0.0, *, cd_prior: float, rate_annual_percent: float) -> CDResult:
    """CD balance and quarterly interest. Verified slope: Δinterest = Δdeposit × rate/4/100 (EXP-01).

    Negative deposits are rejected by the server (``checkResult.ok = false``); this function raises instead.
    The ``cd_prior`` and ``withdraw`` terms follow the working hypothesis and were 0 in EXP-01.
    """
    if deposit < 0 or withdraw < 0:
        raise ValueError("server rejects negative deposit/withdraw (input error)")
    cd = cd_prior + deposit - withdraw
    return CDResult(cd=cd, interest=cd * rate_annual_percent / 4 / 100)


@dataclass(frozen=True)
class CapacityOption:
    units: float
    cost: float
    machines: int | None = None


@dataclass(frozen=True)
class CapacityResult:
    expansion: float
    acquirement: float
    total: float


def capacity_investment(increase_units: float, options: Sequence[CapacityOption]) -> CapacityResult:
    """Capital cost of a fixed-capacity increase = cost of the chosen option row (EXP-02, residual 0)."""
    for option in options:
        if option.units == increase_units:
            return CapacityResult(expansion=option.cost, acquirement=0.0, total=option.cost)
    raise ValueError("increase must equal one of the offered capacity options")


def quarterly_units(units_per_day: float) -> float:
    """Client-side conversion shown on capacity screens (65 production days per quarter)."""
    return units_per_day * DAYS_PER_QUARTER


@dataclass(frozen=True)
class Outlet:
    key: str
    opened: bool
    setup_cost: float
    lease_cost: float


@dataclass(frozen=True)
class OpeningCostResult:
    total_setup: float
    total_lease: float
    total_close: float
    total: float


def _opening_cost(outlets: Iterable[Outlet], changes: Mapping[str, bool]) -> OpeningCostResult:
    setup = 0.0
    for outlet in outlets:
        if not changes.get(outlet.key, False):
            continue
        if outlet.opened:
            raise NotImplementedError("closing an opened outlet is not verified (totalClose, recurring lease)")
        setup += outlet.setup_cost
    # Verified: opening in this quarter adds setup cost only; totalLease and totalClose stay 0.
    return OpeningCostResult(total_setup=setup, total_lease=0.0, total_close=0.0, total=setup)


def store_opening_cost(cities: Iterable[Outlet], changes: Mapping[str, bool]) -> OpeningCostResult:
    """OpenSalesOffice: opening unopened stores (EXP-11; each of 4 cities alone, residual 0)."""
    return _opening_cost(cities, changes)


def web_center_opening_cost(regions: Iterable[Outlet], changes: Mapping[str, bool]) -> OpeningCostResult:
    """OpenWebcenter: opening an unopened regional web sales center (EXP-12; residual 0)."""
    return _opening_cost(regions, changes)


@dataclass(frozen=True)
class StockIssue:
    shares: float
    price: float


@dataclass(frozen=True)
class StockResult:
    stock_increase: float
    shares_increase: float
    stock_total: float
    shares_total: float


def stock_issue(issues: Iterable[StockIssue], *, stock_total_prior: float, shares_total_prior: float) -> StockResult:
    """Closely held stock: increase = Σ shares × price; totals = prior + increase (view identity)."""
    items = list(issues)
    stock_increase = sum(item.shares * item.price for item in items)
    shares_increase = sum(item.shares for item in items)
    return StockResult(stock_increase, shares_increase, stock_total_prior + stock_increase,
                       shares_total_prior + shares_increase)
