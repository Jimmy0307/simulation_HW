"""Local-only sales-to-capacity review; no Marketplace requests or writes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from marketplace_mcp.experiments.q2_planning import (
    brand_cost_quotes,
    evaluate_cash_gates,
    plan_sales_to_capacity,
    read_har_views,
    reconcile_quarters,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile Q1-Q2 and plan Q2 capacity from Sales estimates"
    )
    parser.add_argument("--har", type=Path, required=True, help="Private local HAR")
    parser.add_argument(
        "--sales", type=Path, help='JSON: {"brand_demand": {"brand": units}}'
    )
    parser.add_argument(
        "--cash", type=Path, help="JSON with three observed pro forma cash results"
    )
    parser.add_argument(
        "--output", type=Path, help="Optional local path inside a 'private' folder"
    )
    args = parser.parse_args()
    views = read_har_views(json.loads(args.har.read_text(encoding="utf-8")))
    demand = (
        json.loads(args.sales.read_text(encoding="utf-8"))["brand_demand"]
        if args.sales else None
    )
    cash = json.loads(args.cash.read_text(encoding="utf-8")) if args.cash else None
    static_capacity = views.get("OperatingCapacity", {}).get("staticData", {})
    fixed = int(static_capacity.get("fixedCapacity", 0))
    productivity = float(static_capacity.get("workersProductivity", 0))
    results = {
        "cash_bridge": reconcile_quarters(views),
        "observed_cost_quotes": brand_cost_quotes(views),
        "capacity": plan_sales_to_capacity(
            demand, maximum_daily_capacity=fixed, productivity_pct=productivity
        ) if fixed and productivity else {"status": "MISSING_CAPACITY_VIEW"},
        "cash_gates": evaluate_cash_gates(cash),
        "model_limit": "Not a reconstruction of the Marketplace PHP simulation.",
    }
    output = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        if "private" not in args.output.parts:
            raise ValueError("Refusing to export game-specific values outside a 'private' path")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
