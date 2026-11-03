"""Literature-level demand: published functional forms with uncalibrated coefficients.

Chain (docs/demand-model-spec.md):
  potential per city x segment -> attraction (MNL utility x MCI marketing terms) -> share with an outside option
  -> units per offer. Every output is tagged ``Level.LITERATURE``: the forms have published support, the coefficients
  are literature midpoints or labelled defaults, and nothing here is calibrated on any game. Not a forecast.

Coefficient defaults: ``data/demand_literature.json`` (public, from literature; override the location with the
``MPSIM_DEMAND_DEFAULTS`` environment variable). A parameter pack may override them under
``demand.coefficients``. A fitted, validated coefficient set turns the same form into ``FittedDemand`` (estimated).
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from marketplace_sim.modules import Offer
from marketplace_sim.pack import ParamPack, Segment
from marketplace_sim.provenance import Level, Tagged

_UTILITY_CLAMP = 50.0
_MAX_RELATIVE_PRICE = 10.0
COEFFICIENT_SCHEMA = "marketplace-sim/demand-coefficients@1"
FITTED_SCHEMA = "marketplace-sim/fitted-demand@1"
# Acceptance thresholds for promoting fitted coefficients to "estimated" (project choice; docs/demand-model-spec.md §6).
MAX_HOLDOUT_MAPE = 0.20
MIN_DIRECTION_HIT_RATE = 0.70


DEFAULTS_FILE = Path(__file__).resolve().parents[2] / "data" / "demand_literature.json"


def default_coefficients() -> dict[str, Any]:
    path = Path(os.environ.get("MPSIM_DEMAND_DEFAULTS", str(DEFAULTS_FILE)))
    if not path.exists():
        raise FileNotFoundError(f"literature demand defaults not found at {path}; set MPSIM_DEMAND_DEFAULTS")
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != COEFFICIENT_SCHEMA:
        raise ValueError(f"{path} is not a {COEFFICIENT_SCHEMA} file")
    return dict(data["coefficients"])


def coefficients_for(pack: ParamPack, overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Defaults <- pack ``demand.coefficients`` <- explicit overrides. Unknown keys are rejected."""
    coeffs = default_coefficients()
    for source in (pack.demand.get("coefficients") or {}, overrides or {}):
        unknown = set(source) - set(coeffs)
        if unknown:
            raise ValueError(f"unknown demand coefficient(s): {', '.join(sorted(unknown))}")
        coeffs.update(source)
    if coeffs["ad_shape"] not in {"power", "adbudg"}:
        raise ValueError("ad_shape must be 'power' or 'adbudg'")
    if not 0 <= float(coeffs["carryover"]) < 1:
        raise ValueError("carryover must be in [0, 1)")
    return coeffs


def need_similarity(a: Segment, b: Segment) -> float:
    """Cosine similarity of centred need profiles (index - 100), clipped at 0; 1 for the same segment."""
    if a.id == b.id:
        return 1.0
    keys = sorted(set(a.needs) | set(b.needs))
    va = [float(a.needs.get(k, 100.0)) - 100.0 for k in keys]
    vb = [float(b.needs.get(k, 100.0)) - 100.0 for k in keys]
    na, nb = math.sqrt(sum(x * x for x in va)), math.sqrt(sum(x * x for x in vb))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, sum(x * y for x, y in zip(va, vb, strict=True)) / (na * nb))


@dataclass
class DemandDetail:
    """Per-offer units plus the totals needed downstream (market share, category demand)."""

    units: dict[tuple[str, str], float] = field(default_factory=dict)
    potential: float = 0.0  # total quarterly potential across cells where at least one offer is present
    inside_units: float = 0.0  # units bought from any firm (potential minus outside option)


class LiteratureDemand:
    """MNL/MCI attraction demand with an outside option; see the module docstring and docs/demand-model-spec.md."""

    level = Level.LITERATURE
    name = "LiteratureDemand"

    def __init__(self, coefficients: Mapping[str, Any] | None = None, pack: ParamPack | None = None) -> None:
        if pack is not None:
            self.coefficients = coefficients_for(pack, coefficients)
        else:
            self.coefficients = {**default_coefficients(), **(coefficients or {})}

    @property
    def carryover(self) -> float:
        return float(self.coefficients["carryover"])

    def goodwill(self, offer: Offer) -> float:
        """Our brands carry an explicit stock; rivals are taken to be in steady state a / (1 - lambda)."""
        if offer.ad_stock is not None:
            return max(offer.ad_stock, 0.0)
        return max(offer.advertising, 0.0) / (1.0 - self.carryover)

    def _ad_response(self, stock: float, reference: float) -> float:
        c = self.coefficients
        ratio = stock / reference if reference > 0 else 0.0
        if c["ad_shape"] == "adbudg":
            power = ratio ** float(c["adbudg_c"])
            return float(1.0 + (float(c["adbudg_max"]) - 1.0) * power / (1.0 + power))
        return float((1.0 + ratio) ** float(c["ad_elasticity"]))

    def detail(self, pack: ParamPack, offers: Sequence[Offer]) -> DemandDetail:
        c = self.coefficients
        segments = {s.id: s for s in pack.segments}
        result = DemandDetail()
        # Goodwill reference per segment: a share of quarterly potential revenue across all cities.
        reference = {sid: float(c["ad_reference_share"]) * sum(m.segments[sid].size_12m / 4 * m.segments[sid].wtp
                                                               for m in pack.markets if sid in m.segments)
                     for sid in segments}
        for market in pack.markets:
            for sid, cell in market.segments.items():
                if cell.wtp <= 0 or cell.size_12m <= 0:
                    continue
                attractions: list[tuple[Offer, float]] = []
                for offer in offers:
                    coverage = offer.coverage_in(market.key)
                    if coverage <= 0 or offer.price <= 0:
                        continue
                    position = segments.get(offer.position or offer.segment_id)
                    similarity = need_similarity(position, segments[sid]) if position and sid in segments else (
                        1.0 if (offer.position or offer.segment_id) == sid else 0.0)
                    fit = max(0.0, min(offer.quality, 1.0)) * similarity ** float(c["similarity_power"])
                    if fit <= 0:
                        continue
                    relative_price = min(offer.price / cell.wtp, _MAX_RELATIVE_PRICE)
                    utility = float(c["fit_weight"]) * (fit - 1.0) - float(c["price_sensitivity"]) * (relative_price - 1.0)
                    utility = max(-_UTILITY_CLAMP, min(_UTILITY_CLAMP, utility))
                    attraction = (math.exp(utility) * self._ad_response(self.goodwill(offer), reference.get(sid, 0.0))
                                  * coverage ** float(c["distribution_elasticity"]))
                    attractions.append((offer, attraction))
                if not attractions:
                    continue
                potential = cell.size_12m / 4
                denominator = math.exp(float(c["outside_utility"])) + sum(a for _, a in attractions)
                result.potential += potential
                for offer, attraction in attractions:
                    units = potential * attraction / denominator
                    key = (offer.firm, offer.brand)
                    result.units[key] = result.units.get(key, 0.0) + units
                    result.inside_units += units
        return result

    def units(self, pack: ParamPack, offers: Sequence[Offer]) -> dict[tuple[str, str], Tagged]:
        detail = self.detail(pack, offers)
        source = f"{self.name}: potential x attraction / (outside + sum attraction) (docs/demand-model-spec.md)"
        return {k: Tagged(v, self.level, source) for k, v in detail.units.items()}


def load_fitted_coefficients(model_path: str | Path) -> dict[str, Any]:
    """Read a private fitted-demand file and refuse it unless its hold-out validation passes."""
    path = Path(model_path)
    if not path.exists():
        raise NotImplementedError(f"FittedDemand needs a fitted model file ({path}); see docs/demand-model-spec.md §6")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != FITTED_SCHEMA:
        raise ValueError(f"{path} is not a {FITTED_SCHEMA} file")
    validation = data.get("validation") or {}
    mape, hits = validation.get("mape"), validation.get("direction_hit_rate")
    if mape is None or hits is None or float(mape) > MAX_HOLDOUT_MAPE or float(hits) < MIN_DIRECTION_HIT_RATE:
        raise ValueError(f"fitted demand failed hold-out validation (need MAPE <= {MAX_HOLDOUT_MAPE:.0%} and "
                         f"direction hit rate >= {MIN_DIRECTION_HIT_RATE:.0%}); stay at literature level")
    coefficients: dict[str, Any] = dict(data["coefficients"])
    return coefficients


def demand_for(pack: ParamPack) -> Any:
    """The pack's demand model: ``demand.model`` = literature (default) | placeholder | fitted (with ``model_path``)."""
    from marketplace_sim import modules as m

    kind = str(pack.demand.get("model", "literature"))
    if kind == "literature":
        return LiteratureDemand(pack=pack)
    if kind == "placeholder":
        return m.PlaceholderDemand()
    if kind == "fitted":
        ref = Path(str(pack.demand.get("model_path", "fitted_demand.json")))
        if not ref.is_absolute() and pack.path is not None:
            ref = pack.path.parent / ref
        return m.FittedDemand(str(ref), pack=pack)
    raise ValueError(f"unknown demand model '{kind}' (literature | placeholder | fitted)")
