"""Financing: short- and long-term loans, dividends. HEURISTIC.

The cash arithmetic is exact (proceeds in, principal and interest out, dividends out) and the module's balances
reconcile every quarter (tests/test_business_modules.py). What is not known is the game's rules: interest rates,
limits, terms and how repayment is scheduled were not observed (inferred from the game's menus; awaiting capture),
so the rates and the schedule are labelled practice defaults and every line is heuristic.

* short-term loan: borrowed for one quarter, repaid in full at the start of the next with interest on it;
* long-term loan: principal repaid in equal quarterly instalments over the chosen term, interest on the balance at
  quarter start; extra repayment allowed;
* dividends: paid out of cash this quarter (a financing flow, not an expense).

Loan proceeds, repayments and dividends are ``financing`` flows (cash, not profit); interest is an expense.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

from marketplace_sim.business.base import (
    Field,
    Maturity,
    Metric,
    ModuleDecisionError,
    ModuleInput,
    ModuleResult,
    ModuleSpec,
    read_fields,
)
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

H = Level.HEURISTIC
NOTE = "practice rule: game loan terms unobserved, labelled defaults"
TERMS = (("4", "4 季"), ("8", "8 季"), ("12", "12 季"))


class FinancingModule:
    spec = ModuleSpec(
        key="finance.loans", title="貸款與股利",
        rows={"finance.loans": Maturity.HEURISTIC, "finance.dividends": Maturity.HEURISTIC},
        decisions=("short_loan", "long_loan", "long_term", "extra_repayment", "dividend"),
        outputs=("loan_interest", "loan_short_proceeds", "loan_short_repaid", "loan_long_proceeds", "loan_long_repaid",
                 "dividends_paid", "loan_balance_short", "loan_balance_long"),
        couplings=("financing", "expenses", "state"), evidence="src/marketplace_sim/business/finance.py")
    fields = (Field("short_loan", "短期貸款（下季還清）", "finance.loans", "number", 0, 5_000_000, 10000, 0),
              Field("long_loan", "長期貸款（新借）", "finance.loans", "number", 0, 10_000_000, 10000, 0),
              Field("long_term", "長期貸款期數", "finance.loans", "choice", default="8", options=TERMS),
              Field("extra_repayment", "長期貸款提前還款", "finance.loans", "number", 0, 10_000_000, 10000, 0),
              Field("dividend", "發放股利（總額）", "finance.dividends", "number", 0, 5_000_000, 10000, 0))
    ui: ClassVar[dict[str, Any]] = {"toggle": "借款或發股利", "practice": "現金的進出是精確的算術，但利率、期數、上限都是暫定值（遊戲的貸款條件未觀察到）。"
          "借款與還本、股利是現金流（不進損益），利息是費用。",
          "results": [["loan_interest", "利息"], ["loan_balance_short", "短期貸款餘額"], ["loan_balance_long", "長期貸款餘額"],
                      ["dividends_paid", "股利（現金流出）"]]}
    metrics = (
        Metric("loan_interest", H, "short balance x short rate + long balance x long rate (balances at quarter start)",
               "expense", (), NOTE),
        Metric("loan_short_proceeds", H, "plan input", "financing", (), NOTE),
        Metric("loan_short_repaid", H, "- last quarter's short loan", "financing", (), NOTE),
        Metric("loan_long_proceeds", H, "plan input", "financing", (), NOTE),
        Metric("loan_long_repaid", H, "- (instalment + extra repayment), at most the balance", "financing", (), NOTE),
        Metric("dividends_paid", H, "- plan input", "financing", (), NOTE),
        Metric("loan_balance_short", H, "short loan outstanding at quarter end", "report", (), NOTE),
        Metric("loan_balance_long", H, "long loan outstanding at quarter end", "report", (), NOTE),
    )

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}

    def run(self, inp: ModuleInput) -> ModuleResult:
        v = read_fields(self.fields, inp.decisions, [])
        c, s = self.c, inp.state
        short_prior = float(s.get("short", 0.0))
        long_prior = float(s.get("long", 0.0))
        instalment = float(s.get("instalment", 0.0))
        if v["short_loan"] > c["short_limit"]:
            raise ModuleDecisionError(f"short_loan above the practice limit {c['short_limit']:g}")
        interest = short_prior * c["short_rate_quarterly"] + long_prior * c["long_rate_quarterly"]
        scheduled = min(instalment, long_prior)
        extra = min(v["extra_repayment"], long_prior - scheduled)
        long_after = long_prior - scheduled - extra + v["long_loan"]
        if v["long_loan"] > 0:  # new borrowing: re-spread the whole balance over the chosen term
            instalment = long_after / int(v["long_term"])
        out = ModuleResult()
        out.expenses["loan_interest"] = Tagged(interest, H, f"balances at quarter start x quarterly rates ({NOTE})")
        out.financing["loan_short_proceeds"] = Tagged(v["short_loan"], H, f"plan input ({NOTE})")
        out.financing["loan_short_repaid"] = Tagged(-short_prior, H, f"last quarter's short loan repaid ({NOTE})")
        out.financing["loan_long_proceeds"] = Tagged(v["long_loan"], H, f"plan input ({NOTE})")
        out.financing["loan_long_repaid"] = Tagged(-(scheduled + extra), H, f"instalment + extra repayment ({NOTE})")
        out.financing["dividends_paid"] = Tagged(-v["dividend"], H, f"plan input ({NOTE})")
        out.lines["loan_balance_short"] = Tagged(v["short_loan"], H, f"short loan outstanding ({NOTE})")
        out.lines["loan_balance_long"] = Tagged(long_after, H, f"long loan outstanding ({NOTE})")
        if v["dividend"] > 0:
            out.notes.append("dividends are paid from cash; if cash goes negative the emergency loan covers it")
        # Nothing owed: nothing to carry, so the module stops running next quarter.
        owed = v["short_loan"] > 0 or long_after > 1e-9
        out.state = {"short": v["short_loan"], "long": long_after, "instalment": instalment if long_after > 1e-9 else 0.0} \
            if owed else {}
        return out
