"""Read the decisions the team entered in the game (Summary of Decisions screen) into factory orders.

The other departments do not run this simulator: they enter their decisions in the game. A capture of the Summary of
Decisions screen (REA or a browser HAR) holds all of them; this module turns the parts the factory needs into an
orders file for ``mpsim factory``: brands on sale with price, design and the Sales forecast per brand, the operating
capacity, overtime and worker productivity already entered. Output goes under ``evidence/private`` (game data).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _decision(views: Mapping[str, Mapping[str, Any]], run: str) -> dict[str, Any]:
    summary = (views.get("SummaryOfDecisions") or {}).get("staticData") or {}
    for category in summary.get("categories", []):
        for dec in category.get("decisions", []):
            if dec.get("run") == run:
                return dict(dec.get("data") or {})
    view = views.get(run) or {}
    return dict(view)


def orders_from_views(views: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Orders file content: brands on sale (any region), forecast, current factory settings. Pure structure mapping."""
    brands_data = _decision(views, "ModifyBrand")
    all_brands = {b["brandID"]: b for b in (brands_data.get("dynamicData") or {}).get("allBrands", [])}
    pricing = (_decision(views, "Pricing").get("decisions") or {}).get("regions", [])
    on_sale: dict[int, dict[str, Any]] = {}
    for region in pricing:
        for b in region.get("brands", []):
            if b.get("sell"):
                on_sale.setdefault(b["brandID"], {"price": float(b.get("price", 0)), "priority": b.get("priority", 0),
                                                  "rebate": float(b.get("rebate", 0))})
    forecast = {b["brandID"]: float(b.get("demand", 0))
                for b in (_decision(views, "DemandProjection").get("decisions") or {}).get("brands", [])}
    oc = _decision(views, "OperatingCapacity").get("decisions") or {}
    ot = _decision(views, "Overtime").get("decisions") or {}
    orders = []
    for brand_id, sale in sorted(on_sale.items(), key=lambda kv: kv[1]["priority"] or 99):
        b = all_brands.get(brand_id, {})
        orders.append({"name": b.get("brandName", f"brand {brand_id}"), "brand_type": b.get("brandType", ""),
                       "components": [str(x) for x in b.get("brandFeatures", [])], "price": sale["price"],
                       "rebate": sale["rebate"], "priority": sale["priority"], "forecast": forecast.get(brand_id, 0.0)})
    return {
        "orders": orders,
        "schedule": {"operating_capacity": float(oc.get("operatingCapacity", 0)),
                     "productivity": float(oc.get("projectedWorkersProductivity", 0) or 0),
                     "max_overtime_hours": max(float(ot.get("hoursInDay", 8)) - 8.0, 0.0)},
        "warnings": [w for w in (
            "no brand on sale" if not orders else "",
            "Sales forecast is 0 for a brand on sale" if any(o["forecast"] <= 0 for o in orders) else "",
            "operating capacity is 0" if not oc.get("operatingCapacity") else "") if w],
    }
