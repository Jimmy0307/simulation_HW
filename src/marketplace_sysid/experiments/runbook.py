"""Load the human experiment runbook spec and expand it into dry-run experiment designs.

Nothing here contacts Marketplace. Baselines are unknown until an operator reads the
team's current value, so the dry run uses a placeholder baseline and flags it.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marketplace_sysid.experiments.specification import (
    BaselineState,
    DecisionVariable,
    Experiment,
    propose_one_factor_experiment,
)

PLACEHOLDER_BASELINE = 100.0
CHANNELS = {"WHATIF_CALCULATE", "SAVE_THEN_PROFORMA", "NEXT_QUARTER_AFTER_SUBMIT", "CLIENT_FORMULA"}


@dataclass(frozen=True)
class DryRunResult:
    item_id: str
    channel: str
    requires_submit: bool
    requires_teammate_consent: bool
    catalog_field_found: bool
    experiment: dict[str, Any] | None
    problems: list[str]


def load_runbook(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document["experiments"]
    if not isinstance(items, list):
        raise TypeError("runbook experiments must be a list")
    return [dict(item) for item in items]


def _catalog_fields(catalog: dict[str, Any]) -> dict[str, set[str]]:
    return {str(row["module"]): {str(f["field"]) for f in row["fields"]} for row in catalog["decisions"]}


def dry_run(runbook: list[dict[str, Any]], decision_catalog: dict[str, Any]) -> list[DryRunResult]:
    fields = _catalog_fields(decision_catalog)
    results: list[DryRunResult] = []
    for item in runbook:
        problems: list[str] = []
        module, field_name = str(item["module"]), str(item["field"])
        found = field_name in fields.get(module, set())
        if not found:
            problems.append(f"{module}.{field_name} is not in the decision catalog")
        channel = str(item["channel"])
        if channel not in CHANNELS:
            problems.append(f"unknown channel {channel}")
        requires_submit = channel == "NEXT_QUARTER_AFTER_SUBMIT"
        if requires_submit and not item.get("requires_teammate_consent"):
            problems.append("a submit-dependent experiment must require teammate consent")
        if channel == "WHATIF_CALCULATE" and "cancel" not in str(item.get("restore", "")).casefold():
            problems.append("a what-if item must restore with Cancel")
        experiment: Experiment | None = None
        if found and not problems:
            variable = DecisionVariable(
                name=f"{module}.{field_name}",
                unit=item.get("unit"),
                minimum=item.get("minimum"),
                step=float(item["step"]),
                evidence=list(item.get("evidence", [])),
                provenance="REA_STATIC_MODULE",
            )
            baseline = BaselineState({variable.name: PLACEHOLDER_BASELINE}, state_ref="PLACEHOLDER_REPLACE_WITH_OBSERVED")
            experiment = propose_one_factor_experiment(variable, str(item["metrics"][0]), baseline,
                                                       delta=float(item["step"]))
        results.append(DryRunResult(
            item_id=str(item["id"]),
            channel=channel,
            requires_submit=requires_submit,
            requires_teammate_consent=bool(item.get("requires_teammate_consent")),
            catalog_field_found=found,
            experiment=experiment.to_dict() | {"baseline_is_placeholder": True} if experiment else None,
            problems=problems,
        ))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runbook", type=Path, default=Path("data/experiment_runbook.json"))
    parser.add_argument("--catalog", type=Path, default=Path("data/decision_catalog.json"))
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    results = dry_run(load_runbook(args.runbook), catalog)
    print(json.dumps({
        "dry_run": True,
        "items": len(results),
        "valid": sum(1 for r in results if not r.problems),
        "results": [r.__dict__ for r in results],
    }, indent=1))
    if any(r.problems for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
