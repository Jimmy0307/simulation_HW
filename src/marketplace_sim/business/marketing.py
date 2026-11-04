"""Marketing: allocation of each brand's advertising across media. LITERATURE (form published, weights uncalibrated).

Form: the MCI attraction model treats each marketing instrument as its own multiplicative term with its own elasticity
(Cooper & Nakanishi 1988; docs/demand-literature.md section 5). Applied to media, the demand chain's advertising
response becomes a product over media, each with the meta-analytic advertising elasticity split by a weight w_m
(Sum w_m = 1):

    response = Prod_m (1 + s_m x r / w_m) ^ (e x w_m)      r = goodwill / reference, s_m = share of spend in medium m

* one medium carrying everything with w = 1 is exactly the existing single-response curve (1 + r)^e;
* each medium has diminishing returns (concave in s_m), so the best split is s_m = w_m, where the product equals
  the single curve: the literature budget response is kept, and any other split loses part of it;
* e is the demand chain's ``ad_elasticity`` (meta-analytic range, Sethuraman, Tellis & Briesch 2011).

Uncalibrated: the weights w_m (how much of the elasticity each medium carries). No published general ranking of
local, regional, social and search media exists, so they are a labelled neutral default (equal), to be estimated
from Q2+ data (docs/upgrade-protocol.md section 3). Cross-media synergy (Naik & Raman 2003) is not included yet.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from marketplace_sim.business.base import (
    Maturity,
    MediaSplit,
    ModuleDecisionError,
    ModuleInput,
    ModuleResult,
    ModuleSpec,
    number,
)
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

L = Level.LITERATURE
SOURCE = "MCI per-medium advertising response (Cooper & Nakanishi 1988); weights: neutral labelled default"


def mix_index(shares: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Response at reference spend (r = 1) relative to the best split, without the elasticity: 1 at s = w.

    Prod_m (1 + s_m / w_m)^w_m / 2. Reported so the player sees how far a split is from the best one.
    """
    product = 1.0
    for medium, w in weights.items():
        product *= (1 + shares.get(medium, 0.0) / w) ** w
    return product / 2


class MediaMixLiterature:
    spec = ModuleSpec(
        key="marketing.media_mix", title="廣告媒體分配", rows={"marketing.media_mix": Maturity.LITERATURE},
        decisions=("mix[brand][medium]",), outputs=("media_mix_index[brand]",),
        couplings=("media_split",), evidence="src/marketplace_sim/business/marketing.py; docs/demand-literature.md")

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        weights = {str(k): float(v) for k, v in coefficients["media_weights"].items()}
        if not weights or any(w <= 0 for w in weights.values()) or abs(sum(weights.values()) - 1) > 1e-9:
            raise ValueError("media_weights must be positive and sum to 1")
        self.weights = weights

    def shares(self, mix: Mapping[str, Any]) -> dict[str, float]:
        unknown = set(mix) - set(self.weights)
        if unknown:
            raise ModuleDecisionError(f"unknown medium: {', '.join(sorted(unknown))} (use {', '.join(self.weights)})")
        raw = {str(k): number(mix, str(k), 0.0, high=1e9) for k in mix}
        total = sum(raw.values())
        if total <= 0:
            raise ModuleDecisionError("a media mix needs at least one positive share")
        return {m: raw.get(m, 0.0) / total for m in self.weights}

    def run(self, inp: ModuleInput) -> ModuleResult:
        mixes = inp.decisions.get("mix") or {}
        if not isinstance(mixes, Mapping):
            raise ModuleDecisionError("marketing.media_mix: 'mix' must map brand -> {medium: share}")
        out = ModuleResult()
        for brand in inp.brands:
            mix = mixes.get(brand.name)
            if mix is None:
                continue
            shares = self.shares(mix)
            out.media_split[brand.name] = MediaSplit(
                tuple((m, shares[m], self.weights[m]) for m in self.weights), L, SOURCE)
            out.lines[f"media_mix_index[{brand.name}]"] = Tagged(mix_index(shares, self.weights), L,
                                                                 f"Prod (1 + s/w)^w / 2 at reference spend ({SOURCE})")
        unused = set(mixes) - {b.name for b in inp.brands}
        if unused:
            out.notes.append(f"media mix ignored for brands not in this plan: {', '.join(sorted(unused))}")
        return out


def effective_ratio(ratio: float, parts: tuple[tuple[str, float, float], ...]) -> float:
    """The single-response ratio r' with (1 + r') = Prod (1 + s r / w)^w; the demand chain then applies its own
    response (power or ADBUDG) to r'. With one medium carrying everything (w = 1) r' = r."""
    log_sum = sum(w * math.log1p(s * ratio / w) for _m, s, w in parts)
    return math.expm1(log_sum)
