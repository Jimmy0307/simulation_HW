from __future__ import annotations

import json

import pytest

from marketplace_sysid.experiments.interactions import supported_pairs
from marketplace_sysid.experiments.sensitivity import finite_difference
from marketplace_sysid.experiments.specification import (
    ALLOW_FINAL_SUBMIT,
    ALLOW_WRITE,
    BaselineState,
    DecisionVariable,
    propose_one_factor_experiment,
)
from marketplace_sysid.experiments.surrogate import fit_surrogate
from marketplace_sysid.security.redaction import safe_shape


def test_safe_shape_omits_sensitive_values_and_keys() -> None:
    shape = safe_shape({"studentId": "student_1", "cash": 123.4, "email": "user@example.test"})
    serialized = json.dumps(shape)
    assert "student_1" not in serialized
    assert "user@example.test" not in serialized
    assert "123.4" not in serialized
    assert "_sensitive_field_redacted" in serialized


def test_experiment_requires_evidence_and_never_enables_mutation() -> None:
    variable = DecisionVariable(
        "price", minimum=1, maximum=10, step=1,
        evidence=["VERIFIED_RENDERED_HTML"], provenance="VERIFIED_NETWORK_TRACE",
    )
    experiment = propose_one_factor_experiment(variable, "demand", BaselineState({"price": 5}), delta=2)
    assert [item.offset for item in experiment.perturbations] == [0, -2, 2]
    assert experiment.dry_run and experiment.read_only
    assert not ALLOW_WRITE and not ALLOW_FINAL_SUBMIT
    with pytest.raises(ValueError):
        propose_one_factor_experiment(DecisionVariable("x"), "y", BaselineState({"x": 1}))
    with pytest.raises(ValueError):
        propose_one_factor_experiment(variable, "demand", BaselineState({"price": float("inf")}))


def test_sensitivity_and_supported_interactions() -> None:
    result = finite_difference("price", "demand", (10, 50), [(8, 60), (12, 40)])
    assert result.central_difference == -5
    variables = [
        DecisionVariable("price", evidence=["capture"], provenance="VERIFIED_NETWORK_TRACE"),
        DecisionVariable("advertising", evidence=["capture"], provenance="VERIFIED_NETWORK_TRACE"),
        DecisionVariable("unsupported", evidence=["capture"], provenance="VERIFIED_NETWORK_TRACE"),
    ]
    assert supported_pairs(variables) == [("advertising", "price")]


def test_surrogate_is_held_out_and_explicitly_approximate() -> None:
    pytest.importorskip("sklearn")
    rows = [{"price": float(x), "demand": float(40 - 3 * x)} for x in range(20)]
    report = fit_surrogate(rows, metric="demand", inputs=["price"], model="ridge", seed=7)
    assert report.sample_count == 20
    assert report.train_count + report.test_count == 20
    assert report.test_count >= 2
    assert report.provenance == "OBSERVED_SURROGATE"
    assert not report.internal_formula_claim
    assert report.mae < 1.0
    assert report.rmse < 1.0
