"""Inventory: carrying cost of unsold units, and selling off unwanted inventory. Mixed maturity.

LITERATURE part (``supply.inventory_holding``): holding (carrying) cost is a rate per year times the value of the
inventory held, the standard form of inventory theory (Harris 1913 economic order quantity; operations-management
textbooks; measured carrying-cost rates: see data/module_defaults.json ``ranges`` and ``basis``). Applied to units
left at quarter end, valued at the engine's unit cost:

    holding cost = annual_holding_rate / 4 x Sum_brand ending units x unit cost

  The rate must lie in the published range. The unit cost is a placeholder rule, so the cost line is placeholder
  until unit cost is verified (downstream takes the weakest level).

HEURISTIC part (``supply.inventory_selloff``): units sold off at quarter start bring salvage_fraction x unit cost
each. No general published salvage rate applies, so the fraction is a labelled practice default.

The game has an inventory screen family (InventoryControl, TargetReplenishPoint, SellUnwantedInventory) and an
inventory tax parameter (captured Q1 view); how its holding cost and sell-off price work is unverified
(awaiting Q2 capture).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from marketplace_sim.business.base import (
    Maturity,
    ModuleDecisionError,
    ModuleInput,
    ModuleResult,
    ModuleSpec,
    in_range,
    number,
)
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

H, L = Level.HEURISTIC, Level.LITERATURE


class InventoryModule:
    spec = ModuleSpec(
        key="supply.inventory", title="庫存持有成本與出清",
        rows={"supply.inventory_holding": Maturity.LITERATURE, "supply.inventory_selloff": Maturity.HEURISTIC},
        decisions=("sell_off[brand]",), outputs=("inventory_holding_cost", "inventory_selloff_units[brand]",
                                                 "inventory_selloff_proceeds"),
        couplings=("holding_rate", "inventory_release"),
        evidence="src/marketplace_sim/business/inventory.py; data/module_defaults.json (ranges, basis)")

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None,
                 ranges: Mapping[str, Any] | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}
        if ranges is None:
            from marketplace_sim.business.registry import defaults

            ranges = defaults().get("supply.inventory", {}).get("ranges", {})
        for name, (low, high) in (ranges or {}).items():
            in_range(name, self.c[name], float(low), float(high))
        if not 0 <= self.c["salvage_fraction"] <= 1:
            raise ValueError("salvage_fraction must be in [0, 1]")

    def run(self, inp: ModuleInput) -> ModuleResult:
        out = ModuleResult()
        rate = self.c["annual_holding_rate"] / 4
        out.holding_rate = Tagged(rate, L, "annual carrying-cost rate / 4 (inventory theory; published range)")
        sell = inp.decisions.get("sell_off") or {}
        if not isinstance(sell, Mapping):
            raise ModuleDecisionError("supply.inventory: 'sell_off' must map brand -> units")
        for brand in sell:
            units = number(sell, brand, 0.0)
            have = float(inp.inventory.get(brand, 0.0))
            if units > have + 1e-9:
                raise ModuleDecisionError(f"cannot sell off {units:g} units of {brand}: only {have:g} carried in")
            if units > 0:
                out.inventory_release[brand] = Tagged(units, H, "sell-off at quarter start (practice rule)")
                out.lines[f"inventory_selloff_units[{brand}]"] = out.inventory_release[brand]
        if out.inventory_release:
            out.salvage_fraction = self.salvage
        return out

    @property
    def salvage(self) -> Tagged:
        return Tagged(self.c["salvage_fraction"], H, "salvage fraction of unit cost (labelled practice default)")
