"""Product modules: learning curve (LITERATURE), R&D stock (LITERATURE), quality assurance (HEURISTIC).

* ``production.learning_curve``: Wright's (1936) learning curve in the Stanford-B form with prior experience B:
      cost factor = ((cumulative units at mid-quarter + B) / B) ^ log2(progress ratio)
  applied to labour + overhead of each brand (``conversion_factor``). The progress ratio must lie in the centre of the
  published distribution (Dutton & Thomas 1984, 108 cases, centre 80-82 %, as reported by full-text secondary sources;
  data/module_defaults.json ``ranges``). B is a labelled default. A model option: experience is counted from the
  quarter the option is switched on. The game shows a learning-curve parameter on the brand screen (captured Q1
  structure), so its rule may differ: unverified, awaiting Q2 capture.
* ``rnd.feature_development``: R&D spending builds a stock by the perpetual-inventory method with Griliches' 15 % a
  year depreciation (Hall, Mairesse & Mohnen 2010), and the brand's attraction responds with a constant elasticity in
  the published range of R&D output elasticities (0.01-0.25, centred about 0.08). Taking an output elasticity as an
  attraction elasticity is a labelled mapping; the stock reference is a labelled scale default. The spending line is
  heuristic (how the game charges R&D is unobserved).
* ``production.quality``: quality-assurance spend per unit lowers the defect rate; defects lower attraction and cost
  warranty repairs. Only the direction has published support (PIMS, Buzzell & Gale 1987); practice magnitudes. With
  this module on and no spend, defects are modelled at the base rate (without the module they are not modelled).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from marketplace_sim.business.base import (
    Field,
    Maturity,
    Metric,
    ModuleInput,
    ModuleResult,
    ModuleSpec,
    Outcome,
    in_range,
    read_fields,
)
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

L, H = Level.LITERATURE, Level.HEURISTIC
NOTE = "practice rule: labelled defaults, no calibration"


def _ranges(key: str) -> dict[str, Any]:
    from marketplace_sim.business.registry import defaults

    return dict(defaults().get(key, {}).get("ranges", {}))


def _check(key: str, c: Mapping[str, float]) -> None:
    for name, (low, high) in _ranges(key).items():
        in_range(name, c[name], float(low), float(high))


class LearningCurveModule:
    spec = ModuleSpec(
        key="production.learning_curve", title="學習曲線", rows={"production.learning_curve": Maturity.LITERATURE},
        decisions=(), outputs=("learning_factor", "cumulative_units"), couplings=("conversion_factor", "close: state"),
        evidence="src/marketplace_sim/business/product.py; data/module_defaults.json (ranges)")
    fields = ()
    stoppable = True
    ui = {"toggle": "納入學習曲線（模型選項）", "literature": "累積產量每加倍，人工與製造費用降到「進步率」倍（Wright 1936；"
          "進步率在文獻分布中心 80–82%）。經驗從開啟這個選項的那一季開始累計；單位成本本身仍是佔位規則，所以成本仍標 ≈。",
          "results": [["learning_factor[{brand}]", "人工與製造費用倍數"], ["cumulative_units[{brand}]", "累積產量（期初）"]]}
    metrics = (
        Metric("learning_factor[brand]", L, "((cumulative at mid-quarter + B) / B) ^ log2(progress ratio)", "cost",
               ("cumulative_units[brand]",), "Wright 1936, Stanford-B form; ratio in the published centre."),
        Metric("cumulative_units[brand]", L, "units produced since the option was switched on", "report"),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}
        _check(self.spec.key, self.c)

    def factor(self, cumulative: float, units: float) -> float:
        b = math.log2(self.c["progress_ratio"])
        prior = self.c["prior_experience"]
        return float(((cumulative + units / 2 + prior) / prior) ** b)

    def run(self, inp: ModuleInput) -> ModuleResult:
        read_fields(self.fields, inp.decisions, [])
        out = ModuleResult()
        for brand in inp.brands:
            cumulative = float(inp.state.get(brand.name, 0.0))
            f = Tagged(self.factor(cumulative, max(brand.production, 0.0)), L,
                       "Wright learning curve, Stanford-B, progress ratio in the published centre")
            out.conversion_factor[brand.name] = f
            out.lines[f"learning_factor[{brand.name}]"] = f
            out.lines[f"cumulative_units[{brand.name}]"] = Tagged(cumulative, L, "units produced since switched on")
        out.state = dict(inp.state) or {"_on": 1.0}
        return out

    def close(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        state = dict(inp.state) or {"_on": 1.0}
        for brand, units in outcome.units_produced.items():
            state[brand] = state.get(brand, 0.0) + units
        out = ModuleResult()
        out.state = state
        return out


class RnDModule:
    spec = ModuleSpec(
        key="rnd.feature_development", title="研發新功能", rows={"rnd.feature_development": Maturity.LITERATURE},
        decisions=("rnd",), outputs=("rnd_stock", "rnd_factor", "rnd_spending"),
        couplings=("attraction", "expenses", "state"),
        evidence="src/marketplace_sim/business/product.py; data/module_defaults.json (ranges)")
    fields = (Field("rnd", "研發投入（每季）", "rnd.feature_development", "brand_number", 0, 500000, 5000, 0),)
    ui = {"toggle": "投入研發", "literature": "研發累積成「研發存量」（每年折舊 15%，Griliches 慣例），吸引力依文獻範圍內的研發彈性"
          "（0.01–0.25）報酬遞減地提高；把產出彈性當成吸引力彈性是標明的對應假設。",
          "practice": "研發支出怎麼入帳（遊戲規則）未觀察到，支出列是練習。",
          "results": [["rnd_stock[{brand}]", "研發存量"], ["rnd_factor[{brand}]", "研發吸引力倍數"], ["rnd_spending", "研發支出"]]}
    metrics = (
        Metric("rnd_stock[brand]", L, "(1 - quarterly depreciation) x prior stock + spend", "report", (),
               "Perpetual inventory, 15 %/year (Hall, Mairesse & Mohnen 2010)."),
        Metric("rnd_factor[brand]", L, "(1 + stock / reference) ^ R&D elasticity", "demand", ("rnd_stock[brand]",)),
        Metric("rnd_spending", H, "plan input: R&D spend", "expense", (), "How the game charges R&D is unobserved."),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}
        _check(self.spec.key, self.c)
        self.quarterly_keep = (1 - self.c["annual_depreciation"]) ** 0.25

    def run(self, inp: ModuleInput) -> ModuleResult:
        brands = [b.name for b in inp.brands]
        spend = read_fields(self.fields, inp.decisions, brands)["rnd"]
        out = ModuleResult()
        state: dict[str, float] = {}
        for b in sorted(set(brands) | set(inp.state)):
            stock = self.quarterly_keep * float(inp.state.get(b, 0.0)) + spend.get(b, 0.0)
            if stock >= 1.0:
                state[b] = stock
            if b in brands:
                out.lines[f"rnd_stock[{b}]"] = Tagged(stock, L, "perpetual inventory, 15 %/year depreciation")
                factor = (1 + stock / self.c["stock_reference"]) ** self.c["rnd_elasticity"]
                if stock > 0:
                    out.attraction[b] = Tagged(factor, L, "(1 + stock/ref)^e, e in the published R&D elasticity range")
                    out.lines[f"rnd_factor[{b}]"] = out.attraction[b]
        out.expenses["rnd_spending"] = Tagged(sum(spend.values()), H, f"plan input (game charging rule unobserved; {NOTE})")
        out.state = state
        return out


class QualityModule:
    spec = ModuleSpec(
        key="production.quality", title="品質、退貨與保固", rows={"production.quality": Maturity.HEURISTIC},
        decisions=("qa_per_unit",), outputs=("defect_rate", "quality_factor", "warranty_cost"),
        couplings=("unit_cost_add", "attraction", "settle: expenses"), evidence="src/marketplace_sim/business/product.py")
    fields = (Field("qa_per_unit", "每件品管投入", "production.quality", "brand_number", 0, 100, 1, 0),)
    ui = {"toggle": "納入品質與保固", "practice": "每件品管投入降低不良率；不良品降低吸引力並產生保固維修費。只有方向有文獻支持（PIMS），"
          "幅度是暫定值。開啟這個模組但不投入時，不良率按基準值計算。",
          "results": [["defect_rate[{brand}]", "不良率", "percent"], ["quality_factor[{brand}]", "品質吸引力倍數"],
                      ["warranty_cost", "保固維修費"]]}
    metrics = (
        Metric("defect_rate[brand]", H, "base rate x exp(-QA per unit / scale)", "report", (), NOTE),
        Metric("quality_factor[brand]", H, "1 - sensitivity x defect rate", "demand", ("defect_rate[brand]",), NOTE),
        Metric("warranty_cost", H, "units sold x defect rate x unit cost x repair share", "expense",
               ("units_sold[brand]", "unit_cost[brand]"), NOTE),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}

    def defect_rate(self, qa: float) -> float:
        return self.c["base_defect_rate"] * math.exp(-qa / self.c["qa_scale"])

    def run(self, inp: ModuleInput) -> ModuleResult:
        brands = [b.name for b in inp.brands]
        qa = read_fields(self.fields, inp.decisions, brands)["qa_per_unit"]
        out = ModuleResult()
        for b in brands:
            d = self.defect_rate(qa[b])
            out.lines[f"defect_rate[{b}]"] = Tagged(d, H, f"base rate x exp(-QA/scale) ({NOTE})")
            out.attraction[b] = Tagged(max(0.0, 1 - self.c["defect_sensitivity"] * d), H, f"1 - sensitivity x defects ({NOTE})")
            out.lines[f"quality_factor[{b}]"] = out.attraction[b]
            if qa[b] > 0:
                out.unit_cost_add[b] = Tagged(qa[b], H, f"QA spend per unit ({NOTE})")
        return out

    def settle(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        brands = [b.name for b in inp.brands]
        qa = read_fields(self.fields, inp.decisions, brands)["qa_per_unit"]
        parts = [Tagged(outcome.units_sold.get(b, 0.0) * self.defect_rate(qa[b]) * outcome.unit_cost[b].value
                        * self.c["repair_share"], min(H, outcome.unit_cost[b].level), "units x defects x cost x repair")
                 for b in brands if b in outcome.unit_cost]
        out = ModuleResult()
        out.expenses["warranty_cost"] = Tagged(sum(p.value for p in parts), H,
                                               f"units sold x defect rate x unit cost x repair share ({NOTE})")
        return out
