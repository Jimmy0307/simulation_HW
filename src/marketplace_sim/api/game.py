"""Game mode (one quarter = one turn): a thin layer over the existing engine and control plane. No new computation.

* ``setup``  what the game screens need: product types, component groups, cities, segments and willingness to pay,
  read from the loaded pack, plus the engine's own state lines (quarterly capacity). Every number carries a level.
* ``start``  loads the requested data source, starts a new game, and stores the opponents as control-plane
  ``CompetitorSpec`` rows. A difficulty is a fixed mapping onto the existing bots (``baseline`` / ``random``) and their
  existing ``price_factor`` parameter; ``runner.build_competitor`` builds them, exactly as in a scenario.
* calculate (preview) and play go through ``service.preview`` / ``service.play``, which pass those opponents to
  ``engine.advance``. Rival market shares are the engine's own ``rival_share[firm]`` report lines.
"""

from __future__ import annotations

import json
from typing import Any

from marketplace_sim import modules as m
from marketplace_sim.api import service as svc
from marketplace_sim.control.spec import CompetitorSpec
from marketplace_sim.provenance import Level

MAX_OPPONENTS = 6
REPLAY_PANEL = svc.PRIVATE_ROOT / "model" / "demand_panel" / "replay.json"
DEFAULT_THEME = {"product": "產品", "unit": "件", "icon": "box"}

# Difficulty -> existing bot strategy and parameters (control/runner.build_competitor). Descriptions restate the bots.
DIFFICULTIES: dict[str, dict[str, Any]] = {
    "conservative": {"label": "保守", "strategy": "baseline", "params": {"price_factor": 1.1},
                     "description": "BaselineBot：每個區隔一個固定報價（平均願付價格的 90%）再 × 1.10，廣告固定。"},
    "normal": {"label": "普通", "strategy": "baseline", "params": {},
               "description": "BaselineBot 原樣：每個區隔一個固定報價（平均願付價格的 90%），廣告固定。"},
    "aggressive": {"label": "激進", "strategy": "random", "params": {"price_factor": 0.85},
                   "description": "RandomBot（報價為願付價格的 75–105%、廣告 0–60k、隨機鋪貨）再 × 0.85 壓低價格。"},
}
OBJECTIVES = [
    {"id": "cash", "text": "讓期末現金最大化", "metric": "cash_end"},
    {"id": "share", "text": "讓市佔最大化", "metric": "market_share"},
    {"id": "profit", "text": "讓淨利最大化", "metric": "net_income"},
]


def _line(metric: str, value: float, level: Level, source: str) -> dict[str, Any]:
    return svc.decorate_line(metric, {"value": value, "level": level.label, "source": source})


def theme(session: svc.Session) -> dict[str, Any]:
    """Product theme from the data source: pack.json "theme", then a theme.json next to it, else a generic default."""
    found: dict[str, Any] = {}
    pack_file = session.pack_dir / "pack.json"
    if pack_file.exists():
        found = dict(json.loads(pack_file.read_text(encoding="utf-8")).get("theme") or {})
    overlay = session.pack_dir / "theme.json"
    if not found and overlay.exists():
        found = dict(json.loads(overlay.read_text(encoding="utf-8")))
    return {**DEFAULT_THEME, **{k: v for k, v in found.items() if k in DEFAULT_THEME}}


def replay_status(session: svc.Session) -> dict[str, Any]:
    """Real opponents (replay) need the private competitor panel from Q2 on, covering the current quarter."""
    if not session.is_private:
        return {"available": False, "reason": "真實對手只適用 private 資料源。"}
    if not REPLAY_PANEL.exists():
        return {"available": False,
                "reason": "需要 Q2 起的真實對手資料（evidence/private/model/demand_panel/replay.json），目前尚未建立。"}
    quarters = sorted(int(q) for q in json.loads(REPLAY_PANEL.read_text(encoding="utf-8")).get("quarters", {}))
    current = session.state.quarter if session.state else 1
    if len(quarters) < 2 or current not in quarters:
        return {"available": False, "reason": f"對手資料涵蓋的季別 {quarters} 不足（需要至少兩季且含目前的 Q{current}）。"}
    return {"available": True, "reason": "", "quarters": quarters}


def _regions(session: svc.Session) -> list[dict[str, Any]]:
    pack = session.pack
    state = svc._require_state(session)
    markets = {mk.key: mk for mk in pack.markets}
    segment_names = {s.id: s.name for s in pack.segments}
    order: list[str] = []
    for region in [o.region for o in pack.stores] + [w.region for w in pack.web_centers] + [mk.region for mk in pack.markets]:
        if region not in order:
            order.append(region)
    regions = []
    for region in order:
        web = next((w for w in pack.web_centers if w.region == region), None)
        keys = [s.key for s in pack.stores if s.region == region]
        keys += [mk.key for mk in pack.markets if mk.region == region and mk.key not in keys]
        cities = []
        for key in keys:
            store = next((s for s in pack.stores if s.key == key), None)
            market = markets.get(key)
            cities.append({
                "key": key, "name": store.name if store else (market.name if market else key),
                "store": None if store is None else {
                    "open": key in state.stores_open,
                    "setup_cost": _line("store_setup", store.setup_cost, Level.VERIFIED,
                                        "setupCost of this city (EXP-11: opening cost = setupCost)"),
                    "lease_cost": _line("outlet_lease", store.lease_cost, Level.PLACEHOLDER,
                                        "leaseCost of this city (placeholder: lease timing unverified)")},
                "segments": [] if market is None else [
                    {"id": sid, "name": segment_names.get(sid, sid),
                     "size_12m": _line(f"market_size[{key},{sid}]", cell.size_12m, Level.DERIVED,
                                       "pack parameter markets[*].segments.size_12m (published value)"),
                     "wtp": _line(f"market_wtp[{key},{sid}]", cell.wtp, Level.DERIVED,
                                  "pack parameter markets[*].segments.wtp (published value)")}
                    for sid, cell in market.segments.items()],
            })
        regions.append({
            "id": region,
            "web_center": None if web is None else {
                "key": web.key, "name": web.name, "open": web.key in state.web_centers_open,
                "setup_cost": _line("web_center_setup", web.setup_cost, Level.VERIFIED,
                                    "setupCost of this region's web center (EXP-12)"),
                "lease_cost": _line("outlet_lease", web.lease_cost, Level.PLACEHOLDER,
                                    "leaseCost (placeholder: lease timing unverified)")},
            "cities": cities,
        })
    return regions


def state_view(session: svc.Session) -> dict[str, Any]:
    """Current company state plus the engine's quarterly capacity line (modules.quarterly_capacity)."""
    state = svc._require_state(session)
    capacity = m.quarterly_capacity(session.pack, state.fixed_capacity_units)
    return {"state": svc._state_dict(session),
            "capacity_units_per_quarter": _line("capacity_units_per_quarter", capacity.value, capacity.level,
                                                capacity.source)}


def setup(session: svc.Session) -> dict[str, Any]:
    pack = session.pack
    segment_names = {s.id: s.name for s in pack.segments}
    return {
        **svc.pack_info(session),
        **state_view(session),
        "theme": theme(session),
        "max_opponents": MAX_OPPONENTS,
        "difficulties": [{"id": key, **{k: v for k, v in value.items()}} for key, value in DIFFICULTIES.items()],
        "replay": replay_status(session),
        "objectives": OBJECTIVES,
        "game": session.game_meta,
        "brand_types": [{"code": bt.code, "name": bt.name, "segment_id": bt.segment_id,
                         "segment_name": segment_names.get(bt.segment_id or "", ""),
                         "components": [c.id for c in pack.components if m.compatible(c, bt)],
                         "default_components": [c.id for c in m.default_components(pack, bt)]}
                        for bt in pack.brand_types],
        "component_groups": [{"id": g.id, "name": g.name, "required": g.required, "multi": g.multi}
                             for g in pack.component_groups],
        "components": [{"id": c.id, "group": c.group, "name": c.name, "available_quarter": c.available_quarter}
                       for c in pack.components],
        "segments": [{"id": s.id, "name": s.name, "needs": sorted(s.needs, key=lambda n: -s.needs[n])}
                     for s in pack.segments],
        "regions": _regions(session),
        "capacity_options": [{"units": o.units, "machines": o.machines,
                              "cost": _line("capex_capacity", o.cost, Level.VERIFIED,
                                            "cost of this capacity option row (EXP-02)")}
                             for o in pack.capacity_options],
        "presets": svc.plan_presets(session)["presets"],
    }


def start(session: svc.Session, body: dict[str, Any]) -> dict[str, Any]:
    source = str(body.get("source") or ("private" if session.is_private else "synthetic"))
    if source not in {"synthetic", "private"}:
        raise svc.ApiError("source must be 'synthetic' or 'private'")
    if source != ("private" if session.is_private else "synthetic"):
        svc.load_pack_into(session, source)
    opponents = list(body.get("opponents") or [])
    replay = bool(body.get("replay"))
    if not replay and not 1 <= len(opponents) <= MAX_OPPONENTS:
        raise svc.ApiError(f"choose 1 to {MAX_OPPONENTS} opponents")
    for opponent in opponents:
        if str(opponent.get("difficulty")) not in DIFFICULTIES:
            raise svc.ApiError(f"unknown difficulty {opponent.get('difficulty')!r}")
    svc.new_game(session)
    specs: list[CompetitorSpec] = []
    rows: list[dict[str, Any]] = []
    if replay:
        status = replay_status(session)
        if not status["available"]:
            raise svc.ApiError(str(status["reason"]))
        specs = [CompetitorSpec("replay", "replay", {"panel": str(REPLAY_PANEL)})]
        rows = [{"name": "replay", "difficulty": "replay", "label": "真實對手（replay）"}]
    else:
        for i, opponent in enumerate(opponents):
            preset = DIFFICULTIES[str(opponent["difficulty"])]
            name = f"rival-{i + 1}"
            specs.append(CompetitorSpec(name, str(preset["strategy"]), dict(preset["params"])))
            rows.append({"name": name, "difficulty": opponent["difficulty"], "label": preset["label"],
                         "strategy": preset["strategy"], "params": dict(preset["params"])})
    session.competitors = specs
    session.game_meta = {"opponents": rows, "replay": replay, "objective": str(body.get("objective") or ""),
                         "preset": body.get("preset")}
    return setup(session)
