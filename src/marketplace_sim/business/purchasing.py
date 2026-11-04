"""Purchasing: a quarterly volume contract for components. HEURISTIC (practice rule).

Form: an all-units quantity discount (the standard schedule discussed by Dolan 1987 and Monahan 1984): committing to
a component volume earns a discount on the material cost of the units produced under the contract, and units
committed but not produced pay a shortfall fee (take-or-pay). The literature gives the form, but no general discount
magnitudes or breakpoints, so the tiers and the fee are labelled practice defaults: the module is heuristic.

    discount d = tier(contract_units)
    material cost factor = 1 - d x min(production, contract_units) / production
    shortfall fee = max(contract_units - production, 0) x shortfall_fee_per_unit

The factor multiplies the component (material) part of every brand's unit cost this quarter. The game shows
component, scale and supplier parameters (captured Q1 brand and capacity screens), so volume effects exist there in
some form; how they work is unverified (awaiting capture).
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from typing import Any

from marketplace_sim.business.base import Maturity, ModuleInput, ModuleResult, ModuleSpec, number
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

H = Level.HEURISTIC
NOTE = "practice rule: all-units discount form (Dolan 1987), tiers and fee labelled defaults"


class PurchasingHeuristic:
    spec = ModuleSpec(
        key="supply.purchasing", title="採購合約與數量折扣", rows={"supply.purchasing": Maturity.HEURISTIC},
        decisions=("contract_units",), outputs=("purchasing_discount", "material_cost_factor", "purchasing_shortfall_fee"),
        couplings=("material_cost_factor", "expenses"),
        evidence="src/marketplace_sim/business/purchasing.py")

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        tiers = sorted((float(u), float(d)) for u, d in coefficients["discount_tiers"])
        if not tiers or any(not 0 <= d < 1 for _, d in tiers) or any(b[1] < a[1] for a, b in itertools.pairwise(tiers)):
            raise ValueError("discount_tiers must be [units, discount] with discounts in [0, 1), rising with units")
        self.tiers = tiers
        self.fee = float(coefficients["shortfall_fee_per_unit"])

    def discount(self, contract_units: float) -> float:
        d = 0.0
        for units, discount in self.tiers:
            if contract_units >= units:
                d = discount
        return d

    def run(self, inp: ModuleInput) -> ModuleResult:
        contract = number(inp.decisions, "contract_units", 0.0, high=1e7)
        production = sum(max(b.production, 0.0) for b in inp.brands)
        d = self.discount(contract)
        factor = 1 - d * min(production, contract) / production if production > 0 else 1.0
        shortfall = max(contract - production, 0.0)
        out = ModuleResult()
        out.material_cost_factor = Tagged(factor, H, f"1 - discount x covered share ({NOTE})")
        out.lines["purchasing_discount"] = Tagged(d, H, f"tier of the contract volume ({NOTE})")
        out.lines["material_cost_factor"] = out.material_cost_factor
        out.expenses["purchasing_shortfall_fee"] = Tagged(shortfall * self.fee, H, f"unproduced contract units x fee ({NOTE})")
        return out
