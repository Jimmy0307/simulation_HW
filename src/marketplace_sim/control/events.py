"""Event injection. Events act before a quarter is advanced and are composable (applied in listed order).

=======================  ==================================  =====================================================
type                     target                              effect (magnitude m)
=======================  ==================================  =====================================================
``cost_shock``           capacity | stores | web_centers |   cost fields x (1 + m)
                         outlets | components | production
                         | ``*``
``demand_shock``         segment id | ``*``                   12-month market size x (1 + m)
``rate_change``          cd | tax | emergency                 annual rate + m percentage points
``fx_shock``             region key | ``*``                   local willingness to pay and outlet costs x (1 + m)
``competitor_price_cut`` competitor name | ``*``              rival offer prices x (1 + m)   (use m < 0 for a cut)
``supply_disruption``    capacity                            usable capacity x (1 - m)
=======================  ==================================  =====================================================

Events express scenario *assumptions*. The source level of a number still describes the rule that computes it; the
report lists every event that affected a quarter.
"""

from __future__ import annotations

import copy
from typing import Any

from marketplace_sim.control.spec import EventSpec, apply_path
from marketplace_sim.engine import Adjustments

EVENT_TYPES = ("cost_shock", "demand_shock", "rate_change", "fx_shock", "competitor_price_cut", "supply_disruption")
_COST_PATHS = {
    "capacity": ["capacity_options[*].cost"],
    "stores": ["stores[*].setup_cost", "stores[*].lease_cost"],
    "web_centers": ["web_centers[*].setup_cost", "web_centers[*].lease_cost"],
    "components": ["components[*].price"],
    "production": ["production.min_direct_labor", "production.min_overhead_cpu", "production.design_cost"],
}
_COST_PATHS["outlets"] = _COST_PATHS["stores"] + _COST_PATHS["web_centers"]
_COST_PATHS["*"] = [p for key in ("capacity", "outlets", "components", "production") for p in _COST_PATHS[key]]
_RATES = {"cd": "finance.cd_rate_annual_percent", "tax": "finance.tax_rate_percent",
          "emergency": "finance.emergency_rate_min_percent"}


# Metadata for user interfaces (descriptions of the table in the module docstring; no computation).
EVENT_INFO: dict[str, dict[str, Any]] = {
    "cost_shock": {"targets": sorted(_COST_PATHS), "effect": "cost fields x (1 + m)"},
    "demand_shock": {"targets": ["*", "<segment id>"], "effect": "12-month market size x (1 + m)"},
    "rate_change": {"targets": sorted(_RATES), "effect": "annual rate + m percentage points"},
    "fx_shock": {"targets": ["*", "<region key>"], "effect": "local willingness to pay and outlet costs x (1 + m)"},
    "competitor_price_cut": {"targets": ["*", "<competitor name>"], "effect": "rival prices x (1 + m); m < 0 is a cut"},
    "supply_disruption": {"targets": ["capacity"], "effect": "usable capacity x (1 - m), 0 <= m <= 1"},
}


def validate(event: EventSpec) -> None:
    if event.type not in EVENT_TYPES:
        raise ValueError(f"unknown event type '{event.type}' (known: {', '.join(EVENT_TYPES)})")
    if event.type == "cost_shock" and event.target not in _COST_PATHS:
        raise ValueError(f"cost_shock target must be one of {sorted(_COST_PATHS)}")
    if event.type == "rate_change" and event.target not in _RATES:
        raise ValueError(f"rate_change target must be one of {sorted(_RATES)}")
    if event.type == "supply_disruption" and not 0 <= event.magnitude <= 1:
        raise ValueError("supply_disruption magnitude is the lost fraction (0..1)")


def _scale(data: dict[str, Any], path: str, factor: float) -> int:
    return apply_path(data, path, lambda old: old * factor)


def _shift(data: dict[str, Any], path: str, delta: float) -> int:
    def add(old: Any) -> Any:
        return old + delta

    return apply_path(data, path, add)


def apply_events(raw_pack: dict[str, Any], events: list[EventSpec], quarter: int) -> tuple[dict[str, Any], Adjustments]:
    data = copy.deepcopy(raw_pack)
    adjust = Adjustments()
    for event in events:
        validate(event)
        if not event.active(quarter):
            continue
        m = event.magnitude
        label = event.label or f"{event.type}({event.target}, {m:+g})"
        if event.type == "cost_shock":
            for path in _COST_PATHS[event.target]:
                _scale(data, path, 1 + m)
        elif event.type == "demand_shock":
            segment = "*" if event.target == "*" else event.target
            _scale(data, f"markets[*].segments.{segment}.size_12m", 1 + m)
        elif event.type == "rate_change":
            _shift(data, _RATES[event.target], m)
        elif event.type == "fx_shock":
            selector = "[*]" if event.target == "*" else f"[region={event.target}]"
            _scale(data, f"markets{selector}.segments.*.wtp", 1 + m)
            for kind in ("stores", "web_centers"):
                for field in ("setup_cost", "lease_cost"):
                    _scale(data, f"{kind}{selector}.{field}", 1 + m)
        elif event.type == "competitor_price_cut":
            key = event.target
            adjust.rival_price_factor[key] = adjust.rival_price_factor.get(key, 1.0) * (1 + m)
        elif event.type == "supply_disruption":
            adjust.capacity_factor *= 1 - m
        adjust.labels.append(label)
    return data, adjust
