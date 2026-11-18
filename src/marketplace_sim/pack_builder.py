"""Build a private parameter pack from the user's own REA Evidence (never run on, or shipped with, public data).

Reads the latest captured ``view`` response of each source screen via ``marketplace_sysid.parameters.collect`` and maps
it onto the pack schema (see ``pack.SOURCE_MAP``). The output directory must lie inside a ``private`` directory.

Inputs: REA Evidence under ``evidence/private`` and, as a fallback, plain browser HAR exports (``--har``). A quarter's
capture rarely opens every screen, so ``--base`` merges the new values over the previous private pack: anything this
capture does not show (for example the web-center screen once the center is open) is kept from the base pack.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketplace_sim.pack import SCHEMA, SOURCE_MAP, pack_from_dict
from marketplace_sysid.parameters import Response, collect


def _latest_views(responses: list[Response]) -> dict[str, dict[str, Any]]:
    """Latest ``view`` result per screen. A report shown for an earlier quarter is kept apart as ``Service@Q<n>``."""
    views: dict[str, dict[str, Any]] = {}
    for response in responses:
        if response.method != "view" or not isinstance(response.result, dict):
            continue
        result = response.result
        if not (result.get("staticData") or result.get("dynamicData")):
            continue
        current = (result.get("commonData") or {}).get("currentQuarter")
        key = response.service
        if response.quarter is not None and current is not None and response.quarter != current:
            key = f"{response.service}@Q{response.quarter}"
        views[key] = result
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
    if not web:  # web-center screen not captured: take the open flag from the web sales screen, costs from --base
        web = [{"key": f"R{r['regionID']}", "region": f"R{r['regionID']}", "name": str(r.get("regionName", r["regionID"])),
                "opened": bool(r.get("opened"))}
               for r in (views.get("HireWebSalesPeople", {}).get("staticData") or {}).get("regions", [])]

    groups = brand.get("componentGroups", [])
    brand_types = []
    for bt in brand.get("brandTypes", []):
        mask = int(bt.get("featureType", 0))
        segment = str(mask.bit_length()) if mask and mask & (mask - 1) == 0 else None  # bit k -> segment k+1 (assumed)
        brand_types.append({"code": bt["brandType"], "name": bt["name"], "type_mask": mask, "segment_id": segment,
                            "price_adj": bt.get("priceAdj", 1), "cost_adj": bt.get("costAdj", 1)})
    data = {
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
    _add_capture_extras(data, views)
    return data


_PRODUCTION_EXTRAS = (("var_direct_labor", "varDirectLabor"), ("var_overhead_cpu", "varOverheadCPU"),
                      ("learn_curve", "learnCurve"), ("learn_curve_floor", "learnCurveFloor"),
                      ("scale_threshold", "scaleThreshold"), ("component_threshold", "componentThresholdNumber"),
                      ("factory_cost_index", "factoryCostIndex"), ("workers_productivity", "workersProductivity"),
                      ("min_increase_cost", "minIncreaseCost"), ("var_increase_cpu", "varIncreaseCPU"),
                      ("min_decrease_cost", "minDecreaseCost"), ("var_decrease_cpu", "varDecreaseCPU"))
_FINANCE_EXTRAS = (("short_loan_rate_min_percent", "slRateMin"), ("short_loan_rate_max_percent", "slRateMax"),
                   ("emergency_rate_increment_percent", "elRateInc"), ("long_loan_rate_5yr_percent", "ltRate5yr"),
                   ("inventory_tax_percent", "inventoryTax"))


def _add_capture_extras(data: dict[str, Any], views: dict[str, dict[str, Any]]) -> None:
    """Screen parameters beyond the core pack: cost table, factory, loans, sales-force and media costs (all optional)."""
    brand = views.get("ModifyBrand", {}).get("staticData") or {}
    brand_dyn = views.get("ModifyBrand", {}).get("dynamicData") or {}
    production = data["production"]
    for k_out, k_in in _PRODUCTION_EXTRAS:
        if k_in in brand:
            production[k_out] = float(brand[k_in])
    if "workersDailyCompensation" in brand_dyn:
        production["workers_daily_compensation"] = float(brand_dyn["workersDailyCompensation"])
    cash_flow = views.get("ProFormaCashFlow", {}).get("staticData") or {}
    for k_out, k_in in _FINANCE_EXTRAS:
        if k_in in cash_flow:
            data["finance"][k_out] = float(cash_flow[k_in])

    estimates = []
    for b in (views.get("CostOfProduction", {}).get("dynamicData") or {}).get("brands", []):
        points = [[float(e["units"]), float(e["cost"])] for e in b.get("cogsEstimates", []) if float(e.get("cost", 0)) > 0]
        if points:
            estimates.append({"brand_type": str(b["brandType"]), "components": [str(x) for x in b["brandFeatures"]],
                              "points": sorted(points)})
    if estimates:
        data["cost_estimates"] = estimates

    extras: dict[str, Any] = {}
    hire = views.get("HireSalesPeople", {}).get("staticData") or {}
    web_hire = views.get("HireWebSalesPeople", {}).get("staticData") or {}
    if hire.get("regions"):
        r = hire["regions"][0]
        comp = [float(c["annualCompensation"]) for c in r.get("cities", []) if c.get("annualCompensation")]
        extras["sales_force"] = {
            "hire_cost": float(r.get("hireCost", 0)), "layoff_cost": float(r.get("layOffCost", 0)),
            "support_train_cost": float(r.get("supportTrainCost", 0)),
            "train_cost": {str(sg["segmentID"]): float(sg["trainCost"]) for sg in r.get("segments", [])},
            "annual_compensation": max(comp) if comp else 0.0,
            "web_hire_cost": float((web_hire.get("regions") or [{}])[0].get("hireCost", 0)),
            "web_layoff_cost": float((web_hire.get("regions") or [{}])[0].get("layOffCost", 0)),
        }
        # The game publishes these two costs: they replace the module's practice defaults.
        data.setdefault("modules", {})["sales_force"] = {"hire_cost": extras["sales_force"]["hire_cost"],
                                                         "severance_cost": extras["sales_force"]["layoff_cost"]}
    media = views.get("RegionalMedia", {}).get("staticData") or {}
    if media.get("media"):
        names = {m["mediaID"]: m["mediaName"] for m in media["media"]}
        costs = {m["mediaID"]: m["mediaCost"] for r in media.get("regions", []) for m in r.get("media", [])}
        extras["media"] = [{"id": str(i), "name": names[i], "cost_per_insert": float(costs.get(i, 0))} for i in names]
    web_prod = views.get("WebProductivity", {}).get("staticData") or {}
    if web_prod.get("webProductivities"):
        extras["web_productivity"] = [{"id": str(w["productivityID"]), "setup_cost": float(w["setupCost"]),
                                       "quarterly_budget": float(w["quarterlyBudget"]),
                                       "improvement_percent": float(w["improvement"])}
                                      for w in web_prod["webProductivities"]]
    overtime = views.get("Overtime", {})
    curve = (((overtime.get("dynamicData") or {}).get("graphs") or {}).get("productReduct") or {}).get("data") or []
    if curve:
        xs, ys = curve[0].get("x", []), curve[0].get("y", [])
        extras["overtime_productivity"] = [[float(x), float(y)] for x, y in zip(xs, ys, strict=False)
                                           if abs(float(x) - round(float(x))) < 1e-6]
    if (overtime.get("staticData") or {}).get("overtimeLaborChange"):
        extras["overtime_labor_change"] = [{"overtime": int(o["overtime"]), "change": float(o["change"])}
                                           for o in overtime["staticData"]["overtimeLaborChange"]]
    resources = views.get("FinancialResources", {}).get("staticData") or {}
    if resources.get("futureInvestments") is not None:
        extras["equity_schedule"] = [{"quarter": int(f["quarter"]), "investment": float(f["investment"])}
                                     for f in resources["futureInvestments"]]
    if extras:
        data["extras"] = extras


def merge_over_base(new: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """New capture over the previous pack: empty or missing sections, and outlets the capture did not show, are kept."""
    merged = dict(base)
    for key, value in new.items():
        if key in ("stores", "web_centers"):
            by_key = {o["key"]: o for o in base.get(key, [])}
            for outlet in value:
                by_key[outlet["key"]] = {**by_key.get(outlet["key"], {}), **outlet}
            merged[key] = list(by_key.values())
        elif isinstance(value, dict) and isinstance(base.get(key), dict):
            merged[key] = {**base[key], **value} if value else base[key]
        elif value or key not in base:
            merged[key] = value
    return merged


def build_private_pack(out_dir: Path, evidence_root: Path, har_files: list[Path] | None = None,
                       base: Path | None = None) -> str:
    if "private" not in out_dir.resolve().as_posix().split("/"):
        raise SystemExit("refusing to write a real pack outside a 'private' directory")
    capture = evidence_root / "rea" / "01_capture" / "capture.bundle.json"
    scenarios = sorted(evidence_root.glob("*/rea/*.json"))
    views = _latest_views(collect([capture] if capture.exists() else [], scenarios, har_files or []))
    data = build_pack_dict(views)
    base_file = (base / "pack.json") if base is not None and base.is_dir() else base
    if base_file is not None and base_file.exists():
        data = merge_over_base(data, json.loads(base_file.read_text(encoding="utf-8")))
    for outlet in data.get("web_centers", []) + data.get("stores", []):
        outlet.setdefault("setup_cost", 0.0)  # unknown without the screen or a base pack (flagged below)
        outlet.setdefault("lease_cost", 0.0)
    missing = [o["key"] for o in data.get("web_centers", []) if not o["setup_cost"] and not o["lease_cost"]]
    pack_from_dict(data)  # validate
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pack.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    note = f"; web-center costs unknown for {', '.join(missing)} (pass --base with a pack that has them)" if missing else ""
    return f"private pack written: {out_dir / 'pack.json'} (sources: {', '.join(sorted(views))}){note}"
