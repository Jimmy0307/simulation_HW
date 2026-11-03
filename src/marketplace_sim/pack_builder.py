"""Build a private parameter pack from the user's own REA Evidence (never run on, or shipped with, public data).

Reads the latest captured ``view`` response of each source screen via ``marketplace_sysid.parameters.collect`` and maps
it onto the pack schema (see ``pack.SOURCE_MAP``). The output directory must lie inside a ``private`` directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketplace_sim.pack import SCHEMA, SOURCE_MAP, pack_from_dict
from marketplace_sysid.parameters import Response, collect


def _latest_views(responses: list[Response]) -> dict[str, dict[str, Any]]:
    views: dict[str, dict[str, Any]] = {}
    for response in responses:
        if response.method == "view" and isinstance(response.result, dict) and response.result.get("staticData"):
            views[response.service] = response.result
    return views


def _table(view: dict[str, Any] | None, index: int = 0) -> list[dict[str, Any]]:
    if not view:
        return []
    tables = view["staticData"].get("tables") or []
    return list(tables[index]["items"]) if len(tables) > index else []


def build_pack_dict(views: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cd = views.get("CD", {}).get("staticData", {})
    cash_flow = views.get("ProFormaCashFlow", {}).get("staticData", {})
    capacity = views.get("FixedCapacity", {}).get("staticData", {})
    stock = views.get("Stock", {}).get("staticData", {})
    stores_view = views.get("OpenSalesOffice", {}).get("staticData", {})
    web_view = views.get("OpenWebcenter", {}).get("staticData", {})
    brand = views.get("ModifyBrand", {}).get("staticData", {})
    needs_view = views.get("CustomerNeeds")

    segments = []
    for seg in (needs_view or {}).get("staticData", {}).get("segments", []):
        sid = seg["segmentID"]

        def column(items: list[dict[str, Any]], prefix: str = "", sid: Any = sid) -> dict[str, float]:
            return {prefix + str(i["itemName"]).strip(): float(v["value"]) for i in items for v in i["segments"]
                    if v["segmentID"] == sid}

        segments.append({"id": str(sid), "name": seg["name"],
                         "needs": {**column(_table(needs_view, 0)), **column(_table(needs_view, 1), "web: ")},
                         "use_pattern": column(_table(views.get("UsePattern"), 0))})

    markets: dict[str, dict[str, Any]] = {}
    for item in _table(views.get("MarketSize"), 0):
        key = f"R{item['regionID']}-C{item['cityID']}"
        markets[key] = {"key": key, "region": f"R{item['regionID']}", "name": str(item["itemName"]),
                        "segments": {str(v["segmentID"]): {"size_12m": float(v["value"]), "wtp": 0.0} for v in item["segments"]}}
    for item in _table(views.get("PriceWillingToPay"), 0):
        key = f"R{item['regionID']}-C{item['cityID']}"
        for v in item["segments"]:
            markets.setdefault(key, {"key": key, "region": f"R{item['regionID']}", "name": str(item["itemName"]), "segments": {}})
            markets[key]["segments"].setdefault(str(v["segmentID"]), {"size_12m": 0.0, "wtp": 0.0})["wtp"] = float(v["value"])

    stores = [{"key": f"R{r['regionID']}-C{c['cityID']}", "region": f"R{r['regionID']}",
               "name": str(c.get("cityName", c["cityID"])), "setup_cost": c["setupCost"], "lease_cost": c["leaseCost"],
               "opened": bool(c.get("opened"))} for r in stores_view.get("regions", []) for c in r.get("cities", [])]
    web = [{"key": f"R{r['regionID']}", "region": f"R{r['regionID']}", "name": str(r.get("regionName", r["regionID"])),
            "setup_cost": r["setupCost"], "lease_cost": r["leaseCost"], "opened": bool(r.get("opened"))}
           for r in web_view.get("regions", [])]

    groups = brand.get("componentGroups", [])
    brand_types = []
    for bt in brand.get("brandTypes", []):
        mask = int(bt.get("featureType", 0))
        segment = str(mask.bit_length()) if mask and mask & (mask - 1) == 0 else None  # bit k -> segment k+1 (assumed)
        brand_types.append({"code": bt["brandType"], "name": bt["name"], "type_mask": mask, "segment_id": segment,
                            "price_adj": bt.get("priceAdj", 1), "cost_adj": bt.get("costAdj", 1)})
    return {
        "schema": SCHEMA, "name": "private-from-evidence", "provenance": "private", "days_per_quarter": 65,
        "source_map": SOURCE_MAP,
        "finance": {"cd_rate_annual_percent": cd.get("rate", 0), "tax_rate_percent": cash_flow.get("taxRate", 0),
                    "emergency_rate_min_percent": cash_flow.get("elRateMin", 0)},
        "initial_state": {"cash": cd.get("cash", 0), "cd": cd.get("cd", 0),
                          "fixed_capacity_units": capacity.get("fixedCapacity", 0),
                          "stock_total": stock.get("stockTotal", 0), "shares_total": stock.get("sharesTotal", 0)},
        "capacity_options": [{"units": o["units"], "cost": o["cost"], "machines": o.get("machines")}
                             for o in capacity.get("capacityOptions", [])],
        "stores": stores, "web_centers": web, "segments": segments, "markets": list(markets.values()),
        "component_groups": [{"id": str(g["groupID"]), "name": g["groupName"], "required": bool(g["required"]),
                              "multi": bool(g["multiSelect"])} for g in groups],
        "components": [{"id": str(f["featureID"]), "group": str(g["groupID"]), "name": str(f["featureName"]).strip(),
                        "price": f["featurePrice"], "type_mask": f.get("featureTypes", 0),
                        "available_quarter": f.get("quarterToAppear"), "project_cost": f.get("projectCost", 0)}
                       for g in groups for f in g.get("brandFeatures", [])],
        "brand_types": brand_types,
        "production": {k_out: brand.get(k_in, 0) for k_out, k_in in (
            ("design_cost", "designCost"), ("manufacturing_setup_cost", "manufacturingSetupCost"),
            ("min_direct_labor", "minDirectLabor"), ("min_overhead_cpu", "minOverheadCPU"))},
    }


def build_private_pack(out_dir: Path, evidence_root: Path) -> str:
    if "private" not in out_dir.resolve().as_posix().split("/"):
        raise SystemExit("refusing to write a real pack outside a 'private' directory")
    capture = evidence_root / "rea" / "01_capture" / "capture.bundle.json"
    scenarios = sorted(evidence_root.glob("*/rea/*.json"))
    views = _latest_views(collect([capture] if capture.exists() else [], scenarios))
    data = build_pack_dict(views)
    pack_from_dict(data)  # validate
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pack.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return f"private pack written: {out_dir / 'pack.json'} (sources: {', '.join(sorted(views))})"
