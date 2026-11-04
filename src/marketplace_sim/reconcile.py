"""Statement reconciliation: map engine report lines to the rows of the game's statements, and compare them.

Structure only lives here: row ids and signs of the game's pro-forma statements as captured in Q1 (no values). The
comparison runs on private data only (``evidence/private/reconcile/``), writes its result there, and never prints a
value: each row comes back as ``match`` / ``differs`` / ``not-modeled`` / ``missing``.

How a row moves up (docs/upgrade-protocol.md): a rule-type row (tax, lease, design cost, unit cost, a statement row)
can be promoted to verified only when the engine reproduces the captured row within tolerance on a quarter where the
row is not a structural zero, and on a second quarter as hold-out.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marketplace_sim.provenance import Tagged

# Engine line -> (statement row, sign the engine value takes in that row). Several lines can feed one row.
CASH_ROWS: dict[str, tuple[str, int]] = {
    "revenue": ("sales", +1), "production_cost": ("production", -1), "advertising": ("advertising", -1),
    "store_setup": ("so", -1), "web_center_setup": ("so", -1), "outlet_lease": ("so", -1),
    "sales_force_salaries": ("sf", -1), "sales_force_hiring": ("sf", -1), "sales_force_training": ("sf", -1),
    "sales_force_commission": ("sf", -1), "income_tax": ("income_taxes", -1), "cd_interest": ("interest_income", +1),
    "inventory_selloff_proceeds": ("other_income", +1), "inventory_holding_cost": ("other_exp", -1),
    "purchasing_shortfall_fee": ("other_exp", -1), "capex_capacity": ("fixed_cap", -1), "stock_raised": ("inc_comm", +1),
    "emergency_loan": ("inc_emer_l", +1),
}

# Accrual income statement (needs the accounting.accrual option for COGS and depreciation).
INCOME_ROWS: dict[str, tuple[str, int]] = {
    "revenue": ("sales", +1), "promotion_rebates": ("rebates", -1), "accrual_cogs": ("cogs", -1),
    "rnd_spending": ("rd", -1), "advertising": ("advertising", -1), "internet_marketing": ("inet_exp", -1),
    "sales_force_salaries": ("sf", -1), "sales_force_hiring": ("sf", -1), "sales_force_training": ("sf", -1),
    "sales_force_commission": ("sf", -1), "store_setup": ("so", -1), "outlet_lease": ("so", -1),
    "web_sales_salaries": ("wsc_exp", -1), "web_center_setup": ("wsc_exp", -1), "market_research": ("mr", -1),
    "excess_capacity_cost": ("excess_capacity", -1), "accrual_depreciation": ("depreciation", -1),
    "inventory_selloff_proceeds": ("other_income", +1), "inventory_holding_cost": ("other_exp", -1),
    "purchasing_shortfall_fee": ("other_exp", -1), "inventory_tax": ("other_exp", -1),
    "cd_interest": ("interest_income", +1), "loan_interest": ("interest", -1), "accrual_loss_used": ("loss", -1),
    "income_tax": ("income_taxes", -1), "accrual_net_income": ("net_income", +1),
}
# Candidate mappings that are guesses from row names (unverified): web center costs to wsc_exp, store costs to so.
INCOME_CANDIDATES = {"web_center_setup", "web_sales_salaries", "store_setup", "outlet_lease"}
# Rows of the captured income statement this engine does not produce at all.
INCOME_NOT_MODELED = {"lic_income", "lic_fee", "shipping"}

BALANCE_ROWS: dict[str, tuple[str, int]] = {
    "bs_cash": ("cash", +1), "bs_cd": ("cd", +1), "bs_plant": ("net_fix_ass", +1), "bs_short_loans": ("short_loan", +1),
    "bs_emergency_loans": ("emer_loan", +1), "bs_common_stock": ("common_stock", +1),
    "bs_retained_earnings": ("retained_earnings", +1),
}
# The captured balance sheet has no inventory row and no long-term loan row; our books carry both (labelled).
BALANCE_EXTRA = {"bs_inventory", "bs_long_loans"}


def statement_signs(static_data: Mapping[str, Any]) -> dict[str, int]:
    """Row id -> effective sign (section sign x item sign) of a captured statement's static structure."""
    return {item["id"]: int(section["sign"]) * int(item["sign"])
            for section in static_data["sections"] for item in section["items"]}


@dataclass(frozen=True)
class RowCheck:
    row: str
    status: str  # match | differs | not-modeled | missing
    lines: tuple[str, ...]


def compare(lines: Mapping[str, Tagged | float], captured: Mapping[str, float], mapping: Mapping[str, tuple[str, int]],
            *, rel_tol: float = 0.005, abs_tol: float = 1.0) -> list[RowCheck]:
    """Engine lines folded into statement rows (sign applied) against the captured rows. No values in the result."""
    folded: dict[str, float] = {}
    used: dict[str, list[str]] = {}
    for line, (row, sign) in mapping.items():
        if line in lines:
            raw = lines[line]
            value = raw.value if isinstance(raw, Tagged) else float(raw)
            folded[row] = folded.get(row, 0.0) + sign * value
            used.setdefault(row, []).append(line)
    out = []
    for row in sorted(set(captured) | set(folded)):
        if row not in captured:
            out.append(RowCheck(row, "missing", tuple(used.get(row, ()))))
        elif row not in folded:
            out.append(RowCheck(row, "not-modeled", ()))
        else:
            ok = math.isclose(folded[row], float(captured[row]), rel_tol=rel_tol, abs_tol=abs_tol)
            out.append(RowCheck(row, "match" if ok else "differs", tuple(used[row])))
    return out


def write_private_result(path: Path, checks: Mapping[str, list[RowCheck]]) -> None:
    """Statuses only (no values), written under evidence/private."""
    if "private" not in path.parts:
        raise ValueError("reconciliation results are written under evidence/private only")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {name: [{"row": c.row, "status": c.status, "lines": list(c.lines)} for c in rows]
            for name, rows in checks.items()}
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
