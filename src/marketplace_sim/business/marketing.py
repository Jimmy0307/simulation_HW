"""Marketing: allocation of each brand's advertising budget across media. HEURISTIC (practice rule).

The response of demand to the advertising *budget* is already in the literature demand chain (power / ADBUDG response
with goodwill carryover; docs/demand-model-spec.md). What this module adds is the split of that budget across media,
which has no calibrated or literature-backed form in this project yet:

    effective = (sum_m w_m x sqrt(B_m))^2 / sum_m w_m^2          B_m = budget x share_m

* homogeneous of degree 1: doubling every medium doubles the effective budget, so the budget response itself stays
  the literature curve (diminishing returns come from there);
* within one medium the marginal effect falls (square-root term): piling everything into one medium is less effective;
* efficiency = effective / budget is at most 1 (Cauchy-Schwarz) and equals 1 at shares proportional to w_m^2.

Weights ``w_m`` are labelled defaults in ``data/module_defaults.json`` (no source, practice only); a pack may override
them under ``modules.marketing.media_mix``. Next step to literature: docs/upgrade-protocol.md, ledger row
``marketing.media_mix``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from marketplace_sim.business.base import (
    Maturity,
    ModuleDecisionError,
    ModuleInput,
    ModuleResult,
    ModuleSpec,
    number,
)
from marketplace_sim.provenance import Level, Tagged

H = Level.HEURISTIC
RULE = "practice rule: (sum w_m sqrt(B_m))^2 / sum w_m^2 (heuristic: no literature, no calibration)"


class MediaMixHeuristic:
    spec = ModuleSpec(
        key="marketing.media_mix", title="廣告媒體分配", maturity=Maturity.HEURISTIC,
        decisions=("mix[brand][medium]",), outputs=("ad_efficiency[brand]", "effective_advertising[brand]"),
        couplings=("ad_efficiency",), evidence="src/marketplace_sim/business/marketing.py (practice rule)")

    def __init__(self, coefficients: Mapping[str, Any]) -> None:
        self.weights: dict[str, float] = {str(k): float(v) for k, v in coefficients["media_weights"].items()}
        if not self.weights or any(w <= 0 for w in self.weights.values()):
            raise ValueError("media_weights must be positive")

    def efficiency(self, shares: Mapping[str, float]) -> float:
        """Effective budget per unit of budget for a split (shares are normalised; unknown media are refused)."""
        unknown = set(shares) - set(self.weights)
        if unknown:
            raise ModuleDecisionError(f"unknown medium: {', '.join(sorted(unknown))} (use {', '.join(self.weights)})")
        total = sum(shares.values())
        if total <= 0:
            raise ModuleDecisionError("a media mix needs at least one positive share")
        root = sum(self.weights[m] * math.sqrt(s / total) for m, s in shares.items())
        return root * root / sum(w * w for w in self.weights.values())

    def run(self, inp: ModuleInput) -> ModuleResult:
        mixes = inp.decisions.get("mix") or {}
        if not isinstance(mixes, Mapping):
            raise ModuleDecisionError("marketing.media_mix: 'mix' must map brand -> {medium: share}")
        out = ModuleResult()
        for brand, budget in inp.brands:
            mix = mixes.get(brand)
            if mix is None:
                continue
            shares = {str(k): number(mix, str(k), 0.0, high=1e9) for k in mix}
            eff = self.efficiency(shares)
            out.ad_efficiency[brand] = Tagged(eff, H, RULE)
            out.lines[f"ad_efficiency[{brand}]"] = Tagged(eff, H, RULE)
            out.lines[f"effective_advertising[{brand}]"] = Tagged(budget * eff, H, f"advertising x ad_efficiency ({RULE})")
        unused = set(mixes) - {b for b, _ in inp.brands}
        if unused:
            out.notes.append(f"media mix ignored for brands not in this plan: {', '.join(sorted(unused))}")
        return out
