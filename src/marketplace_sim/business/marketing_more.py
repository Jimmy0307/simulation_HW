"""Marketing levers beyond the media split: promotions (rebates), advertising message, internet marketing.

Promotions and the advertising message are HEURISTIC; internet marketing is LITERATURE (its response part). Each
enters demand through a fixed coupling point and carries its own level: downstream of demand takes the weakest.

* ``marketing.promotions``: a per-unit rebate lowers the price the customer weighs by ``perceived_weight x rebate``
  (``price_factor``), so the demand chain's own price response (literature: Bijmolt, van Heerde & Pieters 2005)
  decides the volume effect. The rebate is paid on the share of buyers who redeem (``redemption_rate``). The
  redemption rate lies in the
  range of field rates reported by Pechmann & Silk 2013 (JPP&M review, full text: 7 % for $1, 27 % for $10, 50 % for
  $20 rebates). The perceived weight has no published value (a derivation from one experiment is not one), so the
  price effect, and with it the module, stays heuristic.
* ``marketing.ad_copy``: the advertising message stresses one of the target segment's needs. A message on a need the
  segment values above its average need raises attraction, one below lowers it, by at most ``lift``. Only the
  direction has published support (content moderates advertising response); no general magnitude.
* ``marketing.internet`` (LITERATURE response): company-wide internet marketing spend raises the attraction of every
  offer with a constant-elasticity (log-log) response, in proportion to the web share of our outlets (a labelled
  mapping: internet marketing works through the web channel). The elasticity must lie in [0.003, 0.23]: from the
  bias-corrected advertising meta-analysis (Korkames, Stanley & Stremersch 2026: 10 % more advertising, 0.03-1 % more
  sales) to the online display estimate of Bayer, Srinivasan, Riedl & Skiera 2020 (0.231, firm panel); default 0.05,
  the median short-term elasticity (Sethuraman, Tellis & Briesch 2011). All full text. The spend reference is a
  labelled scale default; the spending line is heuristic (the game's charging rule is unobserved).
"""

from __future__ import annotations

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

H = Level.HEURISTIC
NOTE = "practice rule: no published quantified relation, labelled defaults, no calibration"


def _check(key: str, c: Mapping[str, float]) -> None:
    from marketplace_sim.business.product import _check as check

    check(key, c)


class PromotionsModule:
    spec = ModuleSpec(
        key="marketing.promotions", title="促銷（回饋金）", rows={"marketing.promotions": Maturity.HEURISTIC},
        decisions=("rebate",), outputs=("promotion_price_factor", "promotion_rebates"),
        couplings=("price_factor", "settle: expenses"), evidence="src/marketplace_sim/business/marketing_more.py")
    fields = (Field("rebate", "每件回饋金額", "marketing.promotions", "brand_number", 0, 500, 5, 0),)
    ui: ClassVar[dict[str, Any]] = {"toggle": "啟用促銷", "practice": "回饋金讓顧客感受到的價格變低（用需求面的價格反應）；只有一部分買家會真的去兌換。"
          "兌換率在文獻報告的實地範圍內（7–50%，預設 27%），但顧客把回饋金當幾成的「感受比例」沒有文獻數字，是暫定值，所以整個模組仍是練習。",
          "results": [["promotion_price_factor[{brand}]", "顧客感受價格倍數"], ["promotion_rebates", "回饋金支出"]]}
    metrics = (
        Metric("promotion_price_factor[brand]", H, "1 - perceived weight x rebate / price", "demand", (), NOTE),
        Metric("promotion_rebates", H, "sum(units sold x rebate x redemption rate)", "expense", ("units_sold[brand]",), NOTE),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}
        _check(self.spec.key, self.c)

    def run(self, inp: ModuleInput) -> ModuleResult:
        rebate = read_fields(self.fields, inp.decisions, [b.name for b in inp.brands])["rebate"]
        out = ModuleResult()
        for b in inp.brands:
            r = rebate.get(b.name, 0.0)
            if r <= 0 or b.price <= 0:
                continue
            factor = max(0.05, 1 - self.c["perceived_weight"] * r / b.price)
            out.price_factor[b.name] = Tagged(factor, H, f"1 - perceived weight x rebate / price ({NOTE})")
            out.lines[f"promotion_price_factor[{b.name}]"] = out.price_factor[b.name]
        return out

    def settle(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        rebate = read_fields(self.fields, inp.decisions, [b.name for b in inp.brands])["rebate"]
        paid = sum(outcome.units_sold.get(b, 0.0) * r for b, r in rebate.items()) * self.c["redemption_rate"]
        out = ModuleResult()
        out.expenses["promotion_rebates"] = Tagged(paid, H, f"units sold x rebate x redemption rate ({NOTE})")
        return out


MESSAGE_RANK = {"first": 0, "second": 1, "third": 2}


class AdCopyModule:
    spec = ModuleSpec(
        key="marketing.ad_copy", title="廣告訊息", rows={"marketing.ad_copy": Maturity.HEURISTIC},
        decisions=("message",), outputs=("ad_copy_factor",), couplings=("attraction",),
        evidence="src/marketplace_sim/business/marketing_more.py")
    fields = (Field("message", "廣告強調", "marketing.ad_copy", "brand_choice", default="none",
                    options=(("none", "不指定"), ("first", "客群最重視的需求"), ("second", "第二重視的需求"),
                             ("third", "第三重視的需求"))),)
    ui: ClassVar[dict[str, Any]] = {"toggle": "指定廣告訊息", "practice": "廣告強調目標客群重視的需求會加分、強調不重視的會扣分（最多 ± 暫定幅度）；只有方向有文獻支持。",
          "results": [["ad_copy_factor[{brand}]", "訊息吸引力倍數"]]}
    metrics = (Metric("ad_copy_factor[brand]", H, "1 + lift x (weight of the stressed need / mean need weight - 1), "
                      "bounded", "demand", (), NOTE),)

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.lift = float(coefficients["lift"])

    def run(self, inp: ModuleInput) -> ModuleResult:
        message = read_fields(self.fields, inp.decisions, [b.name for b in inp.brands])["message"]
        segments = {s.id: s for s in inp.pack.segments}
        out = ModuleResult()
        for b in inp.brands:
            choice = message.get(b.name, "none")
            seg = segments.get(b.segment or "")
            if choice == "none" or seg is None or not seg.needs or b.advertising <= 0:
                continue
            weights = sorted(seg.needs.values(), reverse=True)
            rank = min(MESSAGE_RANK[choice], len(weights) - 1)
            mean = sum(weights) / len(weights)
            score = max(-1.0, min(1.0, weights[rank] / mean - 1)) if mean > 0 else 0.0
            out.attraction[b.name] = Tagged(1 + self.lift * score, H,
                                            f"1 + lift x (stressed need / mean need - 1) ({NOTE})")
            out.lines[f"ad_copy_factor[{b.name}]"] = out.attraction[b.name]
        return out


class InternetMarketingModule:
    spec = ModuleSpec(
        key="marketing.internet", title="網路行銷", rows={"marketing.internet": Maturity.LITERATURE},
        decisions=("web_spend",), outputs=("internet_factor", "internet_marketing"),
        couplings=("attraction", "expenses"), evidence="src/marketplace_sim/business/marketing_more.py")
    fields = (Field("web_spend", "網路行銷預算（每季）", "marketing.internet", "number", 0, 300000, 5000, 0),)
    ui: ClassVar[dict[str, Any]] = {"toggle": "啟用網路行銷", "literature": "固定彈性、報酬遞減；彈性限定在文獻範圍 0.003–0.23（廣告彈性後設分析到網路展示廣告的估計），"
          "預設 0.05。只對網路中心帶來的那部分市場有效（依網路中心占據點的比例，標明的對應假設）。",
          "practice": "網路行銷支出怎麼入帳（遊戲規則）未觀察到，支出列是練習。",
          "results": [["internet_factor", "網路行銷吸引力倍數"], ["internet_marketing", "網路行銷支出"]]}
    metrics = (
        Metric("internet_factor", Level.LITERATURE, "1 + web share x ((1 + spend / reference)^elasticity - 1)", "demand", (),
               "Elasticity in [0.003, 0.23] (Korkames et al. 2026; Bayer et al. 2020); default 0.05 (Sethuraman et al. 2011)."),
        Metric("internet_marketing", H, "plan input: internet marketing spend", "expense", (), NOTE),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}
        _check(self.spec.key, self.c)

    def run(self, inp: ModuleInput) -> ModuleResult:
        spend = read_fields(self.fields, inp.decisions, [])["web_spend"]
        response = (1 + spend / self.c["spend_reference"]) ** self.c["elasticity"]
        factor = 1 + inp.web_share * (response - 1)
        out = ModuleResult()
        out.expenses["internet_marketing"] = Tagged(spend, H, f"plan input (the game's charging rule is unobserved; {NOTE})")
        out.lines["internet_factor"] = Tagged(factor, Level.LITERATURE,
                                              "1 + web share x ((1 + spend/ref)^e - 1), e in the published range")
        if factor != 1.0:
            for b in inp.brands:
                out.attraction[b.name] = out.lines["internet_factor"]
        if spend > 0 and inp.web_share == 0:
            out.notes.append("no web center open at quarter start: internet marketing has no effect")
        return out
