"""Information modules: market research reports and a practice balanced scorecard. Both HEURISTIC.

* ``marketing.market_research``: buying a report costs a labelled practice price and adds its lines to the report.
  The content is this engine's own estimate (so it carries the demand chain's level, never more); what the game's
  reports contain and cost is unverified (awaiting capture).
* ``strategy.balanced_scorecard``: the four perspectives of Kaplan & Norton (1992): financial, customer, internal
  process, learning and growth. Each is scored 0..1 from this quarter's lines and the total is a weighted sum. No
  published weights exist; the game's ranking formula is unverified. A practice score, not the game's ranking.
"""

from __future__ import annotations

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
    read_fields,
)
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

H = Level.HEURISTIC
NOTE = "practice rule: labelled defaults, no calibration"


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


class MarketResearchModule:
    spec = ModuleSpec(
        key="marketing.market_research", title="市場調查", rows={"marketing.market_research": Maturity.HEURISTIC},
        decisions=("segment_report", "rival_report"), outputs=("market_research", "research_segment_units",
                                                                "research_rival_share"),
        couplings=("expenses", "close: lines"), evidence="src/marketplace_sim/business/research.py")
    fields = (Field("segment_report", "買客群需求報告", "marketing.market_research", "flag", default=False),
              Field("rival_report", "買對手報告", "marketing.market_research", "flag", default=False))
    ui = {"toggle": "購買市場調查", "practice": "報告內容是本引擎自己的估計（等級跟需求鏈一樣，不會更可信）；報告價格是暫定值。",
          "results": [["market_research", "調查費用"], ["research_segment_units[{segment}]", "客群需求量"],
                      ["research_rival_share[{rival}]", "對手市佔"]]}
    metrics = (
        Metric("market_research", H, "reports bought x report price", "expense", (), NOTE),
        Metric("research_segment_units[segment]", Level.LITERATURE, "engine estimate of units demanded per segment",
               "report", ("units_demanded[brand]",), "Copy of the engine's own estimate, at its level."),
        Metric("research_rival_share[firm]", Level.LITERATURE, "engine estimate of a rival's share", "report",
               ("rival_share[firm]",), "Copy of the engine's own estimate, at its level."),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.price = float(coefficients["report_price"])

    def run(self, inp: ModuleInput) -> ModuleResult:
        v = read_fields(self.fields, inp.decisions, [])
        bought = int(v["segment_report"]) + int(v["rival_report"])
        out = ModuleResult()
        out.expenses["market_research"] = Tagged(bought * self.price, H, f"{bought} report(s) x price ({NOTE})")
        return out

    def close(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        v = read_fields(self.fields, inp.decisions, [])
        out = ModuleResult()
        lines = outcome.lines
        if v["segment_report"]:
            by_segment: dict[str, Tagged] = {}
            for b in inp.brands:
                key = f"units_demanded[{b.name}]"
                if key in lines and b.segment:
                    prior = by_segment.get(b.segment)
                    by_segment[b.segment] = lines[key] if prior is None else prior + lines[key]
            for seg, units in sorted(by_segment.items()):
                out.lines[f"research_segment_units[{seg}]"] = Tagged(units.value, units.level,
                                                                    "engine estimate of our units demanded in the segment")
        if v["rival_report"]:
            for key, line in lines.items():
                if key.startswith("rival_share["):
                    out.lines["research_" + key] = Tagged(line.value, line.level, "engine estimate of the rival's share")
        return out


class ScorecardModule:
    spec = ModuleSpec(
        key="strategy.balanced_scorecard", title="平衡計分卡（練習版）",
        rows={"strategy.balanced_scorecard": Maturity.HEURISTIC}, decisions=(),
        outputs=("scorecard_financial", "scorecard_customer", "scorecard_internal", "scorecard_learning",
                 "scorecard_total"), couplings=("close: lines",), evidence="src/marketplace_sim/business/research.py")
    fields = ()
    stoppable = True
    ui = {"toggle": "顯示練習版計分卡（模型選項）", "practice": "四個構面（財務、顧客、內部流程、學習成長）來自 Kaplan & Norton（1992）；"
          "各構面怎麼打分、權重多少都是暫定值，不是遊戲的排名公式。",
          "results": [["scorecard_financial", "財務"], ["scorecard_customer", "顧客"], ["scorecard_internal", "內部流程"],
                      ["scorecard_learning", "學習成長"], ["scorecard_total", "總分（練習）"]]}
    metrics = tuple(Metric(n, H, f, "report", i, NOTE) for n, f, i in [
        ("scorecard_financial", "0.5 + net income / revenue, clipped to 0..1", ("net_income", "revenue")),
        ("scorecard_customer", "market share / reference share, clipped", ("market_share",)),
        ("scorecard_internal", "units produced / capacity, clipped", ("capacity_units_per_quarter",)),
        ("scorecard_learning", "training + R&D spend / revenue / reference, clipped", ("revenue",)),
        ("scorecard_total", "weighted sum of the four perspectives", ()),
    ])

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items() if not isinstance(v, dict)}
        self.weights = {k: float(w) for k, w in coefficients["weights"].items()}

    def run(self, inp: ModuleInput) -> ModuleResult:
        read_fields(self.fields, inp.decisions, [])
        out = ModuleResult()
        out.state = {"on": 1.0}  # a model option: stays on until stopped
        return out

    def close(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        lines, c = outcome.lines, self.c

        def val(key: str) -> float:
            return lines[key].value if key in lines else 0.0

        revenue = val("revenue")
        capacity = val("capacity_units_per_quarter")
        learning_spend = val("sales_force_training") + val("rnd_spending")
        scores = {
            "financial": _clip(0.5 + val("net_income") / revenue) if revenue > 0 else 0.0,
            "customer": _clip(val("market_share") / c["reference_share"]),
            "internal": _clip(sum(outcome.units_produced.values()) / capacity) if capacity > 0 else 0.0,
            "learning": _clip(learning_spend / revenue / c["reference_learning_share"]) if revenue > 0 else 0.0,
        }
        weights = self.weights
        out = ModuleResult()
        for name, score in scores.items():
            out.lines[f"scorecard_{name}"] = Tagged(score, H, f"practice score 0..1 ({NOTE})")
        total = sum(weights[k] * scores[k] for k in scores) / sum(weights.values())
        out.lines["scorecard_total"] = Tagged(total, H, f"weighted sum, labelled weights (no published weights; {NOTE})")
        out.state = {"on": 1.0}
        return out
