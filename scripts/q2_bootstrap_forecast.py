"""Offline Q2 bootstrap runner. Both input and output must be private.

python scripts/q2_bootstrap_forecast.py --inputs evidence/private/q2_bootstrap_inputs.json --output evidence/private/q2_bootstrap_results.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from marketplace_sim.forecast_bootstrap import bootstrap_plan


def in_private(path: Path) -> bool:
    return "private" in path.resolve().parts


def main() -> None:
    parser = argparse.ArgumentParser(description="Conditional Q2 bootstrap forecast")
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--draws", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20261116)
    args = parser.parse_args()
    if not in_private(args.inputs) or not in_private(args.output):
        raise ValueError("Input and output paths must be inside a private directory")

    source = json.loads(args.inputs.read_text(encoding="utf-8"))
    required = {
        "plans", "cost_quotes", "segment_mountain_weight", "q1_bank_cash",
        "q2_draft_equity", "q2_interest_income", "q2_fixed_cash_by_plan",
    }
    missing = sorted(required - set(source))
    if missing:
        raise ValueError(f"Missing required input fields: {missing}")

    rows = []
    for i, plan in enumerate(source["plans"]):
        for mode in ("store_only", "speculative_web"):
            rows.append(bootstrap_plan(
                plan, source["cost_quotes"],
                mountain_weight=float(source["segment_mountain_weight"]),
                starting_bank=float(source["q1_bank_cash"]),
                financing=float(source["q2_draft_equity"]),
                interest=float(source["q2_interest_income"]),
                fixed_cash=float(source["q2_fixed_cash_by_plan"][plan["name"]]),
                draws=args.draws, seed=args.seed+i, web_mode=mode,
            ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"results": rows, "provenance": "private_operator_inputs"},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"Saved {len(rows)} private bootstrap scenario summaries. No game writes.")


if __name__ == "__main__":
    main()
