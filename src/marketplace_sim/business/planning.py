"""Production planning: an order-up-to replenishment rule (LITERATURE) and a capacity priority order (HEURISTIC).

``supply.replenishment`` (literature form, no coefficient to calibrate): the base-stock / order-up-to policy of
Arrow, Harris & Marschak (1951) and Scarf (1960), with the textbook normal safety stock (Silver, Pyke & Peterson):

    target = mean demand x cover + z x sd(demand) x sqrt(cover)
    production = max(target - inventory at quarter start, 0)

Mean and sd come from this engine's own record of units demanded in the quarters since the rule was switched on
(sd only from two or more quarters, else 0), so the rule's production carries the level of that record (the demand
chain's level, at best literature). ``cover`` (quarters) and ``z`` (safety factor) are the player's choices, not
coefficients. Without a record (the first quarter) the plan's production is used.

``production.scheduling`` (heuristic): when capacity binds, brands get capacity in the player's priority order. The
game's allocation rule is unobserved; the engine's default (plan order) is no better known.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping
from typing import Any, ClassVar

from marketplace_sim.business.base import (
    Field,
    Maturity,
    Metric,
    ModuleInput,
    ModuleResult,
    ModuleSpec,
    Outcome,
    read_fields,
)
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

L, H = Level.LITERATURE, Level.HEURISTIC
FORM = "order-up-to policy (Arrow, Harris & Marschak 1951; Scarf 1960), normal safety stock"
RULES = (("plan", "照計畫量"), ("order_up_to", "補到目標庫存"))


def _key(brand: str, i: int) -> str:
    return f"{brand}|{i}"


class ProductionPlanningModule:
    spec = ModuleSpec(
        key="supply.replenishment", title="補貨與生產排程規則",
        rows={"supply.replenishment": Maturity.LITERATURE, "production.scheduling": Maturity.HEURISTIC},
        decisions=("rule", "cover", "z", "priority"),
        outputs=("replenishment_target", "replenishment_units", "demand_record_mean"),
        couplings=("production_units", "production_order", "state", "close: state"),
        evidence="src/marketplace_sim/business/planning.py")
    fields = (Field("rule", "生產量怎麼定", "supply.replenishment", "brand_choice", default="plan", options=RULES),
              Field("cover", "目標庫存（幾季的平均需求）", "supply.replenishment", "number", 0.25, 3, 0.25, 1.0, " 季"),
              Field("z", "安全係數 z", "supply.replenishment", "number", 0, 3, 0.1, 0.0),
              Field("priority", "產能不夠時的優先順序（1 最先）", "production.scheduling", "brand_number", 1, 9, 1, 5))
    stoppable = True
    ui: ClassVar[dict[str, Any]] = {"toggle": "啟用補貨與排程規則", "literature": "「補到目標庫存」用文獻的訂購點形式：平均需求 × 目標季數 + z × 標準差 × √季數，"
          "減掉期初庫存；需求紀錄來自本引擎自己的估計，所以生產量跟需求鏈同等級（≈）。第一季還沒有紀錄時用計畫量。",
          "practice": "產能不夠時按優先順序分配；遊戲的分配規則未觀察到。",
          "results": [["replenishment_target[{brand}]", "目標庫存"], ["replenishment_units[{brand}]", "規則決定的產量"],
                      ["demand_record_mean[{brand}]", "需求紀錄平均"]]}
    metrics = (
        Metric("demand_record_mean[brand]", L, "mean of the recorded units demanded", "report", ("units_demanded[brand]",)),
        Metric("replenishment_target[brand]", L, "mean x cover + z x sd x sqrt(cover)", "report",
               ("demand_record_mean[brand]",)),
        Metric("replenishment_units[brand]", L, "max(target - inventory at quarter start, 0)", "plan",
               ("replenishment_target[brand]",), "Replaces the plan's production for that brand."),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.window = int(coefficients["record_quarters"])

    def _record(self, state: Mapping[str, float], brand: str) -> list[float]:
        return [state[_key(brand, i)] for i in range(self.window) if _key(brand, i) in state]

    def run(self, inp: ModuleInput) -> ModuleResult:
        brands = [b.name for b in inp.brands]
        v = read_fields(self.fields, inp.decisions, brands)
        record_level = Level(int(inp.state.get("level", int(L))))
        out = ModuleResult()
        for b in brands:
            if v["rule"][b] != "order_up_to":
                continue
            record = self._record(inp.state, b)
            if not record:
                out.notes.append(f"{b}: no demand record yet, the plan's production is used this quarter")
                continue
            mean = statistics.fmean(record)
            sd = statistics.stdev(record) if len(record) >= 2 else 0.0
            target = mean * v["cover"] + v["z"] * sd * math.sqrt(v["cover"])
            units = max(target - inp.inventory.get(b, 0.0), 0.0)
            level = min(L, record_level)
            out.lines[f"demand_record_mean[{b}]"] = Tagged(mean, level, f"mean of {len(record)} recorded quarter(s)")
            out.lines[f"replenishment_target[{b}]"] = Tagged(target, level, f"mean x cover + z x sd x sqrt(cover) ({FORM})")
            out.production_units[b] = Tagged(units, level, f"max(target - inventory, 0) ({FORM})")
            out.lines[f"replenishment_units[{b}]"] = out.production_units[b]
        if "priority" in inp.decisions:
            out.production_order = tuple(sorted(brands, key=lambda b: (v["priority"][b], brands.index(b))))
        out.state = dict(inp.state) or {"level": float(int(L))}
        return out

    def close(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        """Record this quarter's units demanded (newest first, a rolling window)."""
        state = dict(inp.state)
        level = Level(int(state.get("level", int(L))))
        for b in inp.brands:
            key = f"units_demanded[{b.name}]"
            if key not in outcome.lines:
                continue
            record = self._record(state, b.name)
            record = [outcome.lines[key].value, *record][: self.window]
            for i, value in enumerate(record):
                state[_key(b.name, i)] = value
            level = min(level, outcome.lines[key].level)
        state["level"] = float(int(level))
        out = ModuleResult()
        out.state = state
        return out
