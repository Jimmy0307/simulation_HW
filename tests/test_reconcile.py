"""Statement reconciliation: the engine-to-statement mappings against the captured structure (Q1, private, structure
only), the comparison helper, and the Q2 reconciliation run (skipped until the private Q2 file exists).

Nothing here prints a captured value: structure checks compare row ids and signs; the Q2 run writes statuses only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from marketplace_sim import reconcile as rc
from marketplace_sim.engine import CompanyState, Plan, advance
from marketplace_sim.metrics import lookup
from marketplace_sim.pack import load_pack
from marketplace_sim.provenance import Level, Tagged

ROOT = Path(__file__).resolve().parents[1]
Q1 = ROOT / "evidence" / "private" / "extracted" / "nested" / "marketplace-har" / "marketplace-har" / "out" / "q1" / "services"
Q2_FILE = ROOT / "evidence" / "private" / "reconcile" / "q2.json"
Q2_RESULT = ROOT / "evidence" / "private" / "reconcile" / "q2-result.json"


def captured_signs(name: str) -> dict[str, int]:
    return rc.statement_signs(json.loads((Q1 / name).read_text(encoding="utf-8"))["staticData"])


def test_every_mapped_line_is_a_known_metric() -> None:
    for mapping in (rc.CASH_ROWS, rc.INCOME_ROWS, rc.BALANCE_ROWS):
        for line in mapping:
            assert lookup(line) is not None, line


@pytest.mark.skipif(not (Q1 / "ProFormaIncomeStatement.json").exists(), reason="no private capture")
def test_income_mapping_matches_the_captured_structure() -> None:
    signs = captured_signs("ProFormaIncomeStatement.json")
    for line, (row, sign) in rc.INCOME_ROWS.items():
        assert row in signs, row
        assert signs[row] in {sign, 0}, (line, row)  # 0 = a total row (net income): no sign of its own
    mapped = {row for row, _ in rc.INCOME_ROWS.values()}
    totals = {r for r, sign in signs.items() if sign == 0}
    # every captured row is mapped, a total, or listed as not modeled: nothing is silently ignored
    assert set(signs) == mapped | totals | rc.INCOME_NOT_MODELED


@pytest.mark.skipif(not (Q1 / "ProFormaBalanceSheet.json").exists(), reason="no private capture")
def test_balance_mapping_matches_the_captured_structure() -> None:
    signs = captured_signs("ProFormaBalanceSheet.json")
    for line, (row, sign) in rc.BALANCE_ROWS.items():
        assert signs.get(row) == sign, (line, row)
    assert {row for row, _ in rc.BALANCE_ROWS.values()} == {r for r in signs if not r.startswith("e_")}


def test_compare_reports_statuses_not_values() -> None:
    lines = {"revenue": Tagged(1000.0, Level.LITERATURE, ""), "advertising": Tagged(200.0, Level.VERIFIED, ""),
             "income_tax": Tagged(10.0, Level.HEURISTIC, "")}
    captured = {"sales": 1000.0, "advertising": -250.0, "cogs": -400.0}
    checks = {c.row: c for c in rc.compare(lines, captured, rc.INCOME_ROWS)}
    assert checks["sales"].status == "match" and checks["advertising"].status == "differs"
    assert checks["cogs"].status == "not-modeled" and checks["income_taxes"].status == "missing"
    assert all(not any(ch.isdigit() for ch in c.status) for c in checks.values())


def test_results_are_written_under_private_only(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="private"):
        rc.write_private_result(tmp_path / "public" / "x.json", {})
    target = tmp_path / "private" / "x.json"
    rc.write_private_result(target, {"income": [rc.RowCheck("sales", "match", ("revenue",))]})
    assert json.loads(target.read_text(encoding="utf-8"))["income"][0]["status"] == "match"


@pytest.mark.skipif(not Q2_FILE.exists(), reason="awaiting Q2 capture (docs/q2-capture-checklist.md)")
def test_q2_reconciliation_runs_and_records_statuses() -> None:
    spec: dict[str, Any] = json.loads(Q2_FILE.read_text(encoding="utf-8"))
    pack = load_pack(ROOT / spec.get("pack", "evidence/private/model/pack.json"))
    state = CompanyState.initial(pack)
    report = None
    for i, plan_dict in enumerate(spec["plans"]):
        modules: dict[str, Any] = {"accounting.accrual": {}} if i == 0 else {}
        state, report = advance(state, Plan.from_dict({**plan_dict, "modules": {**modules, **plan_dict.get("modules", {})}}), pack)
    assert report is not None
    statements = spec["statements"]
    checks = {"income": rc.compare(report.lines, statements.get("income", {}), rc.INCOME_ROWS),
              "balance": rc.compare(report.lines, statements.get("balance", {}), rc.BALANCE_ROWS),
              "cash": rc.compare(report.lines, statements.get("cash", {}), rc.CASH_ROWS)}
    rc.write_private_result(Q2_RESULT, checks)
    # the harness ran over every captured row; promotion decisions are made from the private result file
    for name, rows in checks.items():
        assert {c.row for c in rows} >= set(statements.get(name, {})), name
