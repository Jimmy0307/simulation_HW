"""Accrual accounting: an income statement on the accrual basis and a balance sheet. HEURISTIC.

The game's statements are accrual (captured Q1 structure: cost of goods sold, depreciation, a loss carry-forward
row, an inventory-tax parameter; structure only, no values). This model option adds that structure on top of the
engine's cash-basis numbers:

* inventory at book value (moving average of unit cost); production is capitalised, cost of goods sold = units sold
  x average cost; units sold off leave at book value;
* plant (capacity bought while the option is on) depreciated straight-line over ``depreciation_quarters``; capacity
  owned before the option was switched on is not on the books (labelled);
* inventory tax = annual rate / 4 x inventory book value at quarter end (a settle expense);
* income tax on accrual pre-tax income after a loss carry-forward (replaces the engine's cash-basis tax);
* balance sheet: cash, CDs, inventory, plant | loans, emergency loans | common stock, retained earnings. The opening
  retained earnings balance the sheet in the quarter the option is switched on; afterwards the sheet balances by
  construction and ``balance_check`` (assets - liabilities - equity) is reported (0 up to rounding; tested).

Every rule here (depreciation life, inventory valuation, the tax rates and carry-forward) is a labelled practice
choice until Q2+ statements are captured, so all lines are heuristic. The identities (the sheet balances, the
carry-forward never goes negative) are tested.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from marketplace_sim.business.base import (
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
NOTE = "practice rule: accrual structure from the captured statement, rules and rates labelled defaults"
FINANCING_LOANS = ("loan_short_proceeds", "loan_short_repaid", "loan_long_proceeds", "loan_long_repaid")


def _tidy(x: float) -> float:
    """Rounding residue of a balanced sheet shows as 0 (not -0.00)."""
    return 0.0 if abs(x) < 1e-6 else x


def _v(lines: Mapping[str, Tagged], key: str) -> float:
    return lines[key].value if key in lines else 0.0


class AccrualAccounting:
    spec = ModuleSpec(
        key="accounting.accrual", title="應計損益表與資產負債表",
        rows={"accounting.balance_sheet": Maturity.HEURISTIC, "accounting.income_statement": Maturity.HEURISTIC},
        decisions=(), outputs=("accrual_cogs", "accrual_depreciation", "inventory_tax", "accrual_pretax",
                               "loss_carryforward", "accrual_net_income", "bs_total_assets", "balance_check"),
        couplings=("settle: expenses", "tax", "close: lines", "state"),
        evidence="src/marketplace_sim/business/accounting.py")
    fields = ()
    stoppable = True
    ui = {"toggle": "用應計基礎記帳（模型選項）", "practice": "照遊戲報表的結構（銷貨成本、折舊、虧損扣抵、庫存稅）另算一份應計損益表和資產負債表，"
          "所得稅改用應計稅前利潤扣掉虧損扣抵後計算。折舊年限、庫存計價、稅率都是暫定值；資產負債表每季都會平衡（有測試）。",
          "results": [["accrual_cogs", "銷貨成本"], ["accrual_depreciation", "折舊"], ["inventory_tax", "庫存稅"],
                      ["accrual_pretax", "應計稅前利潤"], ["loss_carryforward", "可扣抵虧損（期末）"],
                      ["accrual_net_income", "應計淨利"], ["bs_inventory", "存貨（帳面）"], ["bs_plant", "廠房（帳面）"],
                      ["bs_total_assets", "資產合計"], ["bs_liabilities", "負債合計"], ["bs_equity", "權益合計"],
                      ["balance_check", "資產 − 負債 − 權益"]]}
    metrics = tuple(Metric(n, H, f, r, i, NOTE) for n, f, r, i in [
        ("accrual_cogs", "units sold x moving-average unit cost", "report", ("units_sold[brand]", "unit_cost[brand]")),
        ("accrual_depreciation", "plant book value / depreciation quarters", "report", ("capex_capacity",)),
        ("inventory_tax", "annual rate / 4 x inventory book value", "expense", ("unit_cost[brand]",)),
        ("accrual_pretax", "revenue + interest + other income - expenses (production capitalised) - COGS - "
                           "depreciation - book value sold off", "report", ("revenue", "accrual_cogs", "accrual_depreciation")),
        ("loss_carryforward", "losses not yet used against taxable income", "report", ("accrual_pretax",)),
        ("accrual_loss_used", "carried-forward loss used against this quarter's income", "report", ("accrual_pretax",)),
        ("accrual_net_income", "accrual pretax - income tax", "report", ("accrual_pretax", "income_tax")),
        ("bs_cash", "cash at quarter end", "report", ("cash_end",)),
        ("bs_cd", "CDs at quarter end", "report", ("cd_balance",)),
        ("bs_inventory", "inventory at book value", "report", ("accrual_cogs",)),
        ("bs_plant", "plant at book value", "report", ("accrual_depreciation",)),
        ("bs_total_assets", "cash + CDs + inventory + plant", "report", ()),
        ("bs_loans", "loans outstanding", "report", ()),
        ("bs_short_loans", "short-term loans outstanding", "report", ()),
        ("bs_long_loans", "long-term loans outstanding (no such row on the captured Q1 sheet)", "report", ()),
        ("bs_emergency_loans", "emergency loans taken while the option is on", "report", ("emergency_loan",)),
        ("bs_liabilities", "loans + emergency loans", "report", ()),
        ("bs_common_stock", "stock issued", "report", ("stock_raised",)),
        ("bs_retained_earnings", "opening balance + accrual net income - dividends", "report", ("accrual_net_income",)),
        ("bs_equity", "common stock + retained earnings", "report", ()),
        ("balance_check", "assets - liabilities - equity (0 = balances)", "report", ()),
    ])

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}
        self.tax_rate = float((pack.finance if pack else {}).get("tax_rate_percent", 0.0)) / 100
        self._q: dict[str, float] = {}

    def run(self, inp: ModuleInput) -> ModuleResult:
        read_fields(self.fields, inp.decisions, [])
        out = ModuleResult()
        out.state = dict(inp.state) or {"opened": 0.0}
        return out

    # --- after demand -----------------------------------------------------------------------------------------------

    def _books(self, inp: ModuleInput, o: Outcome) -> dict[str, float]:
        """Inventory at moving-average cost, COGS, book value released, depreciation (this quarter)."""
        s = inp.state
        q: dict[str, float] = {"inventory_end": 0.0, "cogs": 0.0, "released_book": 0.0}
        for brand in sorted(set(o.inventory_start) | set(o.inventory_end) | set(o.units_produced)):
            units_start = o.inventory_start.get(brand, 0.0)
            cost = o.unit_cost[brand].value if brand in o.unit_cost else 0.0
            book_start = float(s.get(f"book|{brand}", units_start * cost))  # first quarter: valued at current cost
            released = o.units_released.get(brand, 0.0)
            avg_start = book_start / units_start if units_start > 0 else cost
            book = book_start - released * avg_start
            produced = o.units_produced.get(brand, 0.0)
            units = units_start - released + produced
            book += produced * cost
            avg = book / units if units > 0 else cost
            sold = o.units_sold.get(brand, 0.0)
            # Nothing left: the whole remaining book value is cost of goods sold (no rounding residue on the books).
            book_end = max(book - sold * avg, 0.0) if o.inventory_end.get(brand, 0.0) > 0 else 0.0
            q["cogs"] += book - book_end
            q["released_book"] += released * avg_start
            q["inventory_end"] += book_end
            q[f"book|{brand}"] = book_end
        q["book_start_total"] = sum(float(s.get(f"book|{b}", o.inventory_start.get(b, 0.0) *
                                                (o.unit_cost[b].value if b in o.unit_cost else 0.0)))
                                    for b in o.inventory_start)
        plant_start = float(s.get("plant", 0.0))
        capex = _v(o.lines, "capex_capacity")
        q["depreciation"] = (plant_start + capex) / self.c["depreciation_quarters"]
        q["plant_end"] = plant_start + capex - q["depreciation"]
        q["plant_start"] = plant_start
        return q

    def settle(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        self._q = self._books(inp, outcome)
        out = ModuleResult()
        out.expenses["inventory_tax"] = Tagged(self._q["inventory_end"] * self.c["inventory_tax_annual"] / 4, H,
                                               f"annual rate / 4 x inventory book value ({NOTE})")
        return out

    def tax(self, inp: ModuleInput, outcome: Outcome) -> Tagged:
        q, lines = self._q, outcome.lines
        opex = sum(_v(lines, k) for k in outcome.expense_lines if k != "production_cost")
        other = sum(_v(lines, k) for k in outcome.income_lines)
        pretax = (_v(lines, "revenue") + _v(lines, "cd_interest") + other - opex - q["cogs"] - q["depreciation"]
                  - q["released_book"])
        carried = float(inp.state.get("loss_cf", 0.0))
        if pretax <= 0:
            used, loss_cf = 0.0, carried - pretax
        else:
            used = min(carried, pretax)
            loss_cf = carried - used
        q["pretax"], q["loss_cf"], q["loss_used"] = pretax, loss_cf, used
        taxable = max(pretax - used, 0.0)
        return Tagged(taxable * self.tax_rate, H, f"tax rate x max(accrual pretax - loss carry-forward, 0) ({NOTE})")

    def close(self, inp: ModuleInput, outcome: Outcome) -> ModuleResult:
        q, lines, s, co = self._q, outcome.lines, inp.state, outcome.company
        tax = _v(lines, "income_tax")
        net = q["pretax"] - tax
        dividends = -_v(lines, "dividends_paid")
        loans_end = _v(lines, "loan_balance_short") + _v(lines, "loan_balance_long")
        loans_start = loans_end - sum(_v(lines, k) for k in FINANCING_LOANS)
        emergency_start = float(s.get("emergency", 0.0))
        emergency_end = emergency_start + _v(lines, "emergency_loan")
        if "retained" in s:
            retained_start = float(s["retained"])
        else:  # opening balance: the books start balanced in the quarter the option is switched on
            assets_start = _v(lines, "cash_start") + co["cd_start"] + q["book_start_total"] + q["plant_start"]
            retained_start = assets_start - loans_start - emergency_start - co["stock_start"]
        retained_end = retained_start + net - dividends
        assets = _v(lines, "cash_end") + co["cd"] + q["inventory_end"] + q["plant_end"]
        liabilities = loans_end + emergency_end
        equity = co["stock_total"] + retained_end
        out = ModuleResult()
        for key, value in [("accrual_cogs", q["cogs"]), ("accrual_depreciation", q["depreciation"]),
                           ("accrual_pretax", q["pretax"]), ("loss_carryforward", q["loss_cf"]),
                           ("accrual_loss_used", q["loss_used"]),
                           ("accrual_net_income", net), ("bs_cash", _v(lines, "cash_end")), ("bs_cd", co["cd"]),
                           ("bs_inventory", q["inventory_end"]), ("bs_plant", q["plant_end"]),
                           ("bs_total_assets", assets), ("bs_loans", loans_end),
                           ("bs_short_loans", _v(lines, "loan_balance_short")),
                           ("bs_long_loans", _v(lines, "loan_balance_long")), ("bs_emergency_loans", emergency_end),
                           ("bs_liabilities", liabilities), ("bs_common_stock", co["stock_total"]),
                           ("bs_retained_earnings", retained_end), ("bs_equity", equity),
                           ("balance_check", _tidy(assets - liabilities - equity))]:
            out.lines[key] = Tagged(value, H, NOTE)
        state = {k: v for k, v in q.items() if k.startswith("book|")}
        state.update({"plant": q["plant_end"], "loss_cf": q["loss_cf"], "retained": retained_end,
                      "emergency": emergency_end, "opened": 1.0})
        out.state = state
        return out
