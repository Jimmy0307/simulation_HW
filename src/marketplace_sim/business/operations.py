"""Operations and people: production workers, executives and culture, operating capacity, factory location.

All HEURISTIC. The forms follow general labour and operations economics; the magnitudes are labelled practice
defaults because no published quantified relation could be carried over (see data/module_defaults.json ``basis``):

* ``hr.production_workers``: a wage index against the local market scales the direct-labour part of unit cost and,
  through retention and effort (efficiency wages), worker productivity: productivity = wage_index ^ elasticity,
  bounded. Published labour-supply elasticities to the firm (Sokolova & Sorensen 2021, median about 1.4 - 1.7) are
  about recruitment and separations, not output, so the productivity elasticity has no published value.
* ``hr.executive_and_culture``: participation programmes and an executive bonus pool build a morale stock that raises
  productivity a little. Direction: Doucouliagos 1995 (participation and productivity, meta-analysis); no usable
  coefficient. Morale is only shown when an employee survey is bought.
* ``production.operating_capacity`` (heuristic): extra shifts multiply capacity, each later shift less efficient, with a
  fixed cost per shift. No verified relative efficiency of later shifts exists (Folkard, Lombardi & Tucker 2005 give
  accident risk by shift, +18 % afternoon and +30 % night, not output).
* ``production.overtime`` (LITERATURE capacity response): output against weekly hours is piecewise log-log
  (Pencavel 2015, full text of IZA DP 8129): elasticity about 1 below 49 hours (1.002; 0.9 in Collewet & Sauermann
  2017), 0.172 (s.e. 0.089) at 49 hours and above. Overtime % is taken on a labelled 40-hour regular week. The wage
  premium is 1.5 x (the US statutory floor, 29 U.S.C. 207; the game's rule is unobserved), so the cost is heuristic.
* ``production.factory_location``: moving production to a lower-wage site scales direct labour and adds shipping per
  unit; a move costs a one-off relocation charge.
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
    read_fields,
)
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

H = Level.HEURISTIC
NOTE = "practice rule: labelled defaults, no calibration"


def _floats(coefficients: Mapping[str, Any]) -> dict[str, float]:
    return {k: float(v) for k, v in coefficients.items() if not isinstance(v, (dict, list))}


class ProductionWorkersModule:
    spec = ModuleSpec(
        key="hr.production_workers", title="生產工人薪資與生產力", rows={"hr.production_workers": Maturity.HEURISTIC},
        decisions=("wage_index",), outputs=("worker_productivity", "labor_cost_factor"),
        couplings=("labor_cost_factor", "capacity_factor"), evidence="src/marketplace_sim/business/operations.py")
    fields = (Field("wage_index", "工資水準（1 = 當地行情）", "hr.production_workers", "number", 0.7, 1.5, 0.05, 1.0, " 倍"),)
    ui = {"toggle": "設定生產工人工資", "practice": "工資高於行情：直接人工成本變高，但留任與努力提高、產能略增（效率工資）；"
          "生產力彈性沒有可用的文獻數字，是暫定值。",
          "results": [["worker_productivity", "工人生產力倍數"], ["labor_cost_factor", "直接人工成本倍數"],
                      ["capacity_units_per_quarter", "本季產能"]]}
    metrics = (
        Metric("worker_productivity", H, "wage index ^ productivity elasticity, bounded", "capacity", (), NOTE),
        Metric("labor_cost_factor", H, "wage index (direct labour scales with the wage)", "cost", (), NOTE),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = _floats(coefficients)

    def run(self, inp: ModuleInput) -> ModuleResult:
        w = read_fields(self.fields, inp.decisions, [])["wage_index"]
        c = self.c
        productivity = min(c["max_productivity"], max(c["min_productivity"], w ** c["productivity_elasticity"]))
        out = ModuleResult()
        out.labor_cost_factor = Tagged(w, H, f"wage index x direct labour ({NOTE})")
        out.capacity_factor = Tagged(productivity, H, f"wage index ^ elasticity, bounded ({NOTE})")
        out.lines["labor_cost_factor"] = out.labor_cost_factor
        out.lines["worker_productivity"] = out.capacity_factor
        return out


class CultureModule:
    spec = ModuleSpec(
        key="hr.executive_and_culture", title="主管薪酬、員工參與與人資調查",
        rows={"hr.executive_and_culture": Maturity.HEURISTIC},
        decisions=("participation", "exec_bonus_pct", "survey"),
        outputs=("hr_morale", "culture_productivity", "culture_participation", "culture_survey", "executive_bonus"),
        couplings=("capacity_factor", "expenses", "revenue_rates", "state"),
        evidence="src/marketplace_sim/business/operations.py")
    fields = (Field("participation", "員工參與方案（每季）", "hr.executive_and_culture", "number", 0, 200000, 5000, 0),
              Field("exec_bonus_pct", "主管獎金池（營收的 %）", "hr.executive_and_culture", "number", 0, 5, 0.1, 0, " %"),
              Field("survey", "做員工調查（顯示士氣）", "hr.executive_and_culture", "flag", default=False))
    ui = {"toggle": "啟用人資與文化", "practice": "參與方案與主管獎金累積成「士氣」，士氣讓產能略增；士氣只有買員工調查才看得到。"
          "只有方向有文獻支持（參與與生產力的後設分析），幅度是暫定值。",
          "results": [["hr_morale", "士氣（0–1）"], ["culture_productivity", "士氣生產力倍數"],
                      ["culture_participation", "參與方案費用"], ["executive_bonus", "主管獎金"], ["culture_survey", "調查費用"]]}
    metrics = (
        Metric("hr_morale", H, "decaying morale stock 0..1 from participation and bonus (shown with a survey)", "report",
               (), NOTE),
        Metric("culture_productivity", H, "1 + morale bonus x morale", "capacity", (), NOTE),
        Metric("culture_participation", H, "plan input", "expense", (), NOTE),
        Metric("culture_survey", H, "survey price when bought", "expense", (), NOTE),
        Metric("executive_bonus", H, "revenue x bonus %", "expense", ("revenue",), NOTE),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = _floats(coefficients)

    def morale_after(self, morale: float, participation: float, bonus_pct: float) -> float:
        c = self.c
        target = 1 - math.exp(-participation / c["participation_scale"] - bonus_pct / c["bonus_scale"])
        return morale + c["adjust_speed"] * (target - morale)

    def run(self, inp: ModuleInput) -> ModuleResult:
        v = read_fields(self.fields, inp.decisions, [])
        c = self.c
        morale = self.morale_after(float(inp.state.get("morale", c["initial_morale"])), v["participation"],
                                   v["exec_bonus_pct"])
        out = ModuleResult()
        out.capacity_factor = Tagged(1 + c["morale_bonus"] * morale, H, f"1 + bonus x morale ({NOTE})")
        out.lines["culture_productivity"] = out.capacity_factor
        if v["survey"]:
            out.lines["hr_morale"] = Tagged(morale, H, f"morale stock ({NOTE})")
        out.expenses["culture_participation"] = Tagged(v["participation"], H, f"plan input ({NOTE})")
        out.expenses["culture_survey"] = Tagged(c["survey_price"] if v["survey"] else 0.0, H, f"survey price ({NOTE})")
        out.revenue_rates["executive_bonus"] = Tagged(v["exec_bonus_pct"] / 100, H, f"bonus % of revenue ({NOTE})")
        out.state = {"morale": morale}
        return out


SHIFT_OPTIONS = (("1", "一班"), ("2", "兩班"), ("3", "三班"))


class OperatingCapacityModule:
    spec = ModuleSpec(
        key="production.operating_capacity", title="營運產能：班別與加班",
        rows={"production.operating_capacity": Maturity.HEURISTIC, "production.overtime": Maturity.LITERATURE},
        decisions=("shifts", "overtime_pct"),
        outputs=("shift_factor", "overtime_units", "shift_cost", "overtime_premium"),
        couplings=("capacity_factor", "capacity_extra", "expenses", "settle: expenses"),
        evidence="src/marketplace_sim/business/operations.py")
    fields = (Field("shifts", "班別", "production.operating_capacity", "choice", default="1", options=SHIFT_OPTIONS),
              Field("overtime_pct", "加班（正常工時的 %）", "production.overtime", "number", 0, 50, 1, 0, " %"))
    ui = {"toggle": "設定班別與加班", "literature": "加班的產能反應用文獻的工時–產出關係：每週 49 小時以下產出與工時成正比，"
          "超過後彈性只剩約 0.17（Pencavel 2015）；以每週 40 小時為正常工時（標明的假設）。",
          "practice": "多開一班產能變多但效率較低、每班有固定費用（後班效率沒有文獻數字）；加班工資按 1.5 倍"
          "（美國法定下限，遊戲規則未觀察到），所以成本是練習。",
          "results": [["shift_factor", "班別產能倍數"], ["overtime_units", "加班可多產（件）"], ["capacity_units_per_quarter", "本季產能"],
                      ["shift_cost", "加班別固定費用"], ["overtime_premium", "加班工資加給"]]}
    metrics = (
        Metric("shift_factor", H, "1 + sum of later-shift efficiencies", "capacity", (), NOTE),
        Metric("overtime_units", Level.LITERATURE, "regular capacity x (relative output at 40 x (1 + overtime) hours - 1); "
               "output vs hours piecewise log-log", "capacity", (), "Pencavel 2015: elasticity ~1 below 49 h, 0.172 above."),
        Metric("shift_cost", H, "extra shifts x fixed cost per shift", "expense", (), NOTE),
        Metric("overtime_premium", H, "units made beyond regular capacity x direct labour x (premium - 1)", "expense",
               ("capacity_units_per_quarter",), "Premium 1.5 = US statutory floor (29 U.S.C. 207); game rule unobserved."),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = _floats(coefficients)
        from marketplace_sim.business.product import _check

        _check(self.spec.key, self.c)
        self.labor = float((pack.production if pack else {}).get("min_direct_labor", 0.0))

    def relative_output(self, overtime: float) -> float:
        """Output at regular x (1 + overtime) hours relative to regular hours (Pencavel 2015, piecewise log-log)."""
        c = self.c
        hours = c["regular_hours"] * (1 + overtime)
        if hours <= c["threshold_hours"]:
            return float((1 + overtime) ** c["elasticity_below"])
        at_threshold = (c["threshold_hours"] / c["regular_hours"]) ** c["elasticity_below"]
        return float(at_threshold * (hours / c["threshold_hours"]) ** c["elasticity_above"])

    def _plan(self, inp: ModuleInput) -> tuple[int, float, float, float]:
        v = read_fields(self.fields, inp.decisions, [])
        shifts = int(v["shifts"])
        factor = 1.0 + (self.c["second_shift_efficiency"] if shifts >= 2 else 0.0) + (
            self.c["third_shift_efficiency"] if shifts >= 3 else 0.0)
        regular = inp.capacity_units * factor
        overtime = regular * (self.relative_output(v["overtime_pct"] / 100) - 1)
        return shifts, factor, regular, overtime

    def run(self, inp: ModuleInput) -> ModuleResult:
        shifts, factor, _regular, overtime = self._plan(inp)
        out = ModuleResult()
        if shifts > 1:  # one shift = the plain capacity: nothing to mark
            out.capacity_factor = Tagged(factor, H, f"1 + later-shift efficiencies ({NOTE})")
            out.lines["shift_factor"] = out.capacity_factor
            out.expenses["shift_cost"] = Tagged((shifts - 1) * self.c["shift_fixed_cost"], H,
                                                f"extra shifts x fixed cost ({NOTE})")
        if overtime > 0:
            # Literature unless it rides on a heuristic shift factor.
            level = Level.LITERATURE if shifts == 1 else H
            out.capacity_extra = Tagged(overtime, level, "regular capacity x (relative output of the longer week - 1) "
                                        "(Pencavel 2015 piecewise log-log; 40-hour regular week labelled)")
            out.lines["overtime_units"] = out.capacity_extra
        return out

    def settle(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        _shifts, _factor, regular, _overtime = self._plan(inp)
        # Regular capacity here is before the other capacity modules (productivity), a labelled simplification.
        beyond = max(sum(outcome.units_produced.values()) - regular, 0.0)
        out = ModuleResult()
        if beyond <= 0 and "overtime_units" not in outcome.lines:
            return out
        out.expenses["overtime_premium"] = Tagged(beyond * self.labor * (self.c["overtime_premium"] - 1), H,
                                                  f"units beyond regular capacity x direct labour x (premium - 1) ({NOTE})")
        return out


class ExcessCapacityModule:
    """Idle capacity charge (HEURISTIC). The captured Q1 income statement has an 'excess capacity' expense row
    (structure only), so the game charges something for capacity it does not use; the rule is unobserved. Practice
    rule: unused units x a labelled idle cost per unit. A model option."""

    spec = ModuleSpec(
        key="production.excess_capacity", title="閒置產能成本", rows={"production.excess_capacity": Maturity.HEURISTIC},
        decisions=(), outputs=("idle_capacity_units", "excess_capacity_cost"), couplings=("settle: expenses",),
        evidence="src/marketplace_sim/business/operations.py")
    fields = ()
    stoppable = True
    ui = {"toggle": "計入閒置產能成本（模型選項）", "practice": "遊戲損益表有「閒置產能」費用列（Q1 擷取的結構），但怎麼算沒看到；"
          "這裡用「沒用到的產能 × 暫定單位成本」。",
          "results": [["idle_capacity_units", "閒置產能（件）"], ["excess_capacity_cost", "閒置產能成本"]]}
    metrics = (
        Metric("idle_capacity_units", H, "capacity - units produced", "report", ("capacity_units_per_quarter",), NOTE),
        Metric("excess_capacity_cost", H, "idle units x idle cost per unit", "expense", ("idle_capacity_units",), NOTE),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.rate = float(coefficients["idle_cost_per_unit"])

    def run(self, inp: ModuleInput) -> ModuleResult:
        read_fields(self.fields, inp.decisions, [])
        out = ModuleResult()
        out.state = {"on": 1.0}
        return out

    def settle(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        capacity = outcome.lines["capacity_units_per_quarter"]
        idle = max(capacity.value - sum(outcome.units_produced.values()), 0.0)
        out = ModuleResult()
        out.lines["idle_capacity_units"] = Tagged(idle, min(H, capacity.level), "capacity - units produced")
        out.expenses["excess_capacity_cost"] = Tagged(idle * self.rate, H, f"idle units x idle cost ({NOTE})")
        return out


LOCATIONS = (("home", "原地"), ("low_cost", "低工資地區"))


class FactoryLocationModule:
    spec = ModuleSpec(
        key="production.factory_location", title="工廠與倉庫地點",
        rows={"production.factory_location": Maturity.HEURISTIC}, decisions=("location",),
        outputs=("location_labor_factor", "location_shipping", "relocation_cost"),
        couplings=("labor_cost_factor", "unit_cost_add", "expenses", "state"),
        evidence="src/marketplace_sim/business/operations.py")
    fields = (Field("location", "生產地點", "production.factory_location", "choice", default="home", options=LOCATIONS),)
    ui = {"toggle": "選擇生產地點", "practice": "低工資地區：直接人工較便宜，但每件要多付運費；搬遷要付一次搬遷費。數字都是暫定值。",
          "results": [["location_labor_factor", "直接人工倍數"], ["location_shipping", "每件運費"], ["relocation_cost", "搬遷費"]]}
    metrics = (
        Metric("location_labor_factor", H, "labour factor of the chosen site", "cost", (), NOTE),
        Metric("location_shipping", H, "shipping per unit from the chosen site", "cost", (), NOTE),
        Metric("relocation_cost", H, "one-off charge when the site changes", "expense", (), NOTE),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.sites: dict[str, dict[str, float]] = {k: {a: float(b) for a, b in v.items()}
                                                   for k, v in coefficients["sites"].items()}
        self.relocation = float(coefficients["relocation_cost"])

    def run(self, inp: ModuleInput) -> ModuleResult:
        choice = read_fields(self.fields, inp.decisions, [])["location"] if inp.decisions else None
        codes = [o[0] for o in LOCATIONS]
        current = codes[int(inp.state.get("site", 0))]
        site = choice or current
        out = ModuleResult()
        moved = site != current
        out.expenses["relocation_cost"] = Tagged(self.relocation if moved else 0.0, H, f"one-off move ({NOTE})")
        spec = self.sites[site]
        out.labor_cost_factor = Tagged(spec["labor_factor"], H, f"site labour factor ({NOTE})")
        out.lines["location_labor_factor"] = out.labor_cost_factor
        ship = Tagged(spec["shipping_per_unit"], H, f"shipping per unit ({NOTE})")
        out.lines["location_shipping"] = ship
        if ship.value:
            for b in inp.brands:
                out.unit_cost_add[b.name] = ship
        # Back home: nothing left to carry, the module stops running (and marking numbers) next quarter.
        out.state = {} if site == "home" else {"site": float(codes.index(site))}
        return out
