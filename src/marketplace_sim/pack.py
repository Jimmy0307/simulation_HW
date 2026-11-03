"""Parameter packs: the only way data enters the engine.

A pack is a directory containing ``pack.json`` (schema ``marketplace-sim/param-pack@1``). The public repository ships a
made-up pack in ``examples/synthetic``. Real packs are built privately from the user's own REA Evidence
(``marketplace_sim.pack_builder``) and live under ``evidence/private/model``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA = "marketplace-sim/param-pack@1"

# Where each pack field comes from in data/parameter_catalog.json ("Service:path").
SOURCE_MAP: dict[str, str] = {
    "finance.cd_rate_annual_percent": "CD:staticData.rate",
    "finance.tax_rate_percent": "ProFormaCashFlow:staticData.taxRate",
    "finance.emergency_rate_min_percent": "ProFormaCashFlow:staticData.elRateMin",
    "initial_state.cash": "CD:staticData.cash",
    "initial_state.cd": "CD:staticData.cd",
    "initial_state.fixed_capacity_units": "FixedCapacity:staticData.fixedCapacity",
    "initial_state.stock_total": "Stock:staticData.stockTotal",
    "initial_state.shares_total": "Stock:staticData.sharesTotal",
    "capacity_options[*]": "FixedCapacity:staticData.capacityOptions[*].{units,machines,cost}",
    "stores[*]": "OpenSalesOffice:staticData.regions[*].cities[*].{cityID,setupCost,leaseCost,opened}",
    "web_centers[*]": "OpenWebcenter:staticData.regions[*].{regionID,setupCost,leaseCost,opened}",
    "segments[*].needs": "CustomerNeeds:staticData.tables[*].items[*].segments[*].value",
    "segments[*].use_pattern": "UsePattern:staticData.tables[*].items[*].segments[*].value",
    "markets[*].segments.size_12m": "MarketSize:staticData.tables[*].items[*].segments[*].value",
    "markets[*].segments.wtp": "PriceWillingToPay:staticData.tables[*].items[*].segments[*].value",
    "component_groups[*]": "ModifyBrand:staticData.componentGroups[*].{groupID,required,multiSelect}",
    "components[*]": "ModifyBrand:staticData.componentGroups[*].brandFeatures[*].{featureID,featurePrice,featureTypes,quarterToAppear,projectCost}",
    "brand_types[*]": "ModifyBrand:staticData.brandTypes[*].{brandType,featureType,priceAdj,costAdj}",
    "production.*": "ModifyBrand:staticData.{designCost,manufacturingSetupCost,minDirectLabor,minOverheadCPU}",
}


@dataclass(frozen=True)
class CapacityOption:
    units: float
    cost: float
    machines: int | None = None


@dataclass(frozen=True)
class OutletSpec:
    key: str
    region: str
    name: str
    setup_cost: float
    lease_cost: float
    opened: bool = False


@dataclass(frozen=True)
class Segment:
    id: str
    name: str
    needs: dict[str, float] = field(default_factory=dict)
    use_pattern: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketCell:
    size_12m: float
    wtp: float


@dataclass(frozen=True)
class Market:
    key: str
    region: str
    name: str
    segments: dict[str, MarketCell]


@dataclass(frozen=True)
class ComponentGroup:
    id: str
    name: str
    required: bool
    multi: bool


@dataclass(frozen=True)
class Component:
    id: str
    group: str
    name: str
    price: float
    type_mask: int
    available_quarter: int | None = None
    project_cost: float = 0.0


@dataclass(frozen=True)
class BrandType:
    code: str
    name: str
    type_mask: int
    segment_id: str | None
    price_adj: float = 1.0
    cost_adj: float = 1.0


@dataclass(frozen=True)
class ParamPack:
    name: str
    provenance: str
    days_per_quarter: int
    finance: dict[str, float]
    initial_state: dict[str, float]
    capacity_options: list[CapacityOption]
    stores: list[OutletSpec]
    web_centers: list[OutletSpec]
    segments: list[Segment]
    markets: list[Market]
    component_groups: list[ComponentGroup]
    components: list[Component]
    brand_types: list[BrandType]
    production: dict[str, float]
    path: Path | None = None
    demand: dict[str, Any] = field(default_factory=dict)  # demand model choice and coefficient overrides

    def segment(self, segment_id: str) -> Segment:
        return next(s for s in self.segments if s.id == segment_id)

    def brand_type(self, code: str) -> BrandType:
        return next(b for b in self.brand_types if b.code == code)

    def component(self, component_id: str) -> Component:
        return next(c for c in self.components if c.id == component_id)


def _outlets(rows: list[dict[str, Any]]) -> list[OutletSpec]:
    return [OutletSpec(str(r["key"]), str(r["region"]), str(r.get("name", r["key"])), float(r["setup_cost"]),
                       float(r["lease_cost"]), bool(r.get("opened", False))) for r in rows]


def pack_from_dict(data: dict[str, Any], path: Path | None = None) -> ParamPack:
    if data.get("schema") != SCHEMA:
        raise ValueError(f"not a {SCHEMA} pack")
    return ParamPack(
        name=str(data["name"]),
        provenance=str(data["provenance"]),
        days_per_quarter=int(data.get("days_per_quarter", 65)),
        finance={k: float(v) for k, v in data["finance"].items()},
        initial_state={k: float(v) for k, v in data["initial_state"].items()},
        capacity_options=[CapacityOption(float(o["units"]), float(o["cost"]), o.get("machines")) for o in data["capacity_options"]],
        stores=_outlets(data["stores"]),
        web_centers=_outlets(data["web_centers"]),
        segments=[Segment(str(s["id"]), str(s["name"]), {k: float(v) for k, v in s.get("needs", {}).items()},
                          {k: float(v) for k, v in s.get("use_pattern", {}).items()}) for s in data["segments"]],
        markets=[Market(str(m["key"]), str(m["region"]), str(m.get("name", m["key"])),
                        {str(k): MarketCell(float(v["size_12m"]), float(v["wtp"])) for k, v in m["segments"].items()})
                 for m in data["markets"]],
        component_groups=[ComponentGroup(str(g["id"]), str(g["name"]), bool(g["required"]), bool(g.get("multi", False)))
                          for g in data["component_groups"]],
        components=[Component(str(c["id"]), str(c["group"]), str(c["name"]), float(c["price"]), int(c.get("type_mask", 0)),
                              c.get("available_quarter"), float(c.get("project_cost", 0))) for c in data["components"]],
        brand_types=[BrandType(str(b["code"]), str(b["name"]), int(b.get("type_mask", 0)),
                               None if b.get("segment_id") is None else str(b["segment_id"]),
                               float(b.get("price_adj", 1)), float(b.get("cost_adj", 1))) for b in data["brand_types"]],
        production={k: float(v) for k, v in data.get("production", {}).items()},
        path=path,
        demand=dict(data.get("demand") or {}),
    )


def load_pack(directory: Path) -> ParamPack:
    path = Path(directory) / "pack.json"
    return pack_from_dict(json.loads(path.read_text(encoding="utf-8")), path)
