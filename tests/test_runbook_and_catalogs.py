from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketplace_sysid.experiments.runbook import dry_run, load_runbook

ROOT = Path(__file__).parents[1]


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))
    return data


def test_runbook_dry_run_is_valid_against_published_catalog() -> None:
    results = dry_run(load_runbook(ROOT / "data" / "experiment_runbook.json"), _load("decision_catalog.json"))
    assert results and all(not result.problems for result in results)
    assert all(result.experiment and result.experiment["dry_run"] for result in results)
    assert all(result.experiment and not result.experiment["allow_write"] for result in results)
    assert all(result.requires_teammate_consent for result in results if result.requires_submit)
    ranks = [item["rank"] for item in load_runbook(ROOT / "data" / "experiment_runbook.json")]
    assert ranks == sorted(ranks)


def test_dry_run_rejects_unsafe_items() -> None:
    catalog = {"decisions": [{"module": "M", "fields": [{"field": "f"}]}]}
    items: list[dict[str, Any]] = [
        {"id": "a", "module": "M", "field": "f", "channel": "NEXT_QUARTER_AFTER_SUBMIT", "step": 1,
         "metrics": ["y"], "requires_teammate_consent": False},
        {"id": "b", "module": "M", "field": "f", "channel": "WHATIF_CALCULATE", "step": 1,
         "metrics": ["y"], "restore": "save old value"},
        {"id": "c", "module": "M", "field": "missing", "channel": "WHATIF_CALCULATE", "step": 1,
         "metrics": ["y"], "restore": "Cancel"},
    ]
    results = dry_run(items, catalog)
    assert all(result.problems for result in results)
    assert all(result.experiment is None for result in results)


def test_guard_policy_is_conservative() -> None:
    policy = _load("guard_policy.json")
    strict = policy["strict"]
    assert "save" in strict["methods_any_service"]
    assert {"WrapUp", "Chat", "Email"} <= set(strict["services_all_methods"])
    baseline = set(policy["baseline"]["pairs"])
    experiment = policy["experiment"]["service_methods"]
    # No write method may be allowed by the baseline or experiment tiers.
    assert not any(pair.endswith(".save") for pair in baseline)
    assert all("save" not in methods for methods in experiment.values())
    # Exactly one screen is in the active experiment tier.
    assert list(experiment) == ["FixedCapacity"]
    assert policy["experiment"]["any_service_methods"] == ["view"]
    assert policy["evaluation_order"][:2] == ["baseline", "strict"]


def test_published_catalogs_are_value_free_and_attributed() -> None:
    decisions = _load("decision_catalog.json")
    metrics = _load("metric_catalog.json")
    rpc = _load("rpc_catalog.json")
    assert decisions["values_included"] is False and metrics["values_included"] is False
    assert all(row["provenance"] and row["rea_module_key"] for row in decisions["decisions"])
    assert all(row["provenance"] for row in metrics["metrics"])
    assert rpc["base_decision_methods"]["save"]["class"] == "WRITE"
    assert rpc["base_decision_methods"]["calculate"]["class"] == "CALCULATION_TRIGGER"
    wrap = next(row for row in decisions["decisions"] if row["module"] == "WrapUp")
    assert "continueWrapup" in wrap["view_mode_buttons"]
