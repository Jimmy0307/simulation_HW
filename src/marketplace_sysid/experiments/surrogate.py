"""Optional, explicitly approximate surrogate model evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil, sqrt
from typing import Any

_MODEL_NAMES = {"linear", "ridge", "decision_tree", "random_forest", "gradient_boosting", "gaussian_process"}


@dataclass(frozen=True)
class SurrogateReport:
    model: str
    metric: str
    sample_count: int
    train_count: int
    test_count: int
    r2: float | None
    mae: float
    rmse: float
    empirical_interval: tuple[float, float]
    provenance: str = "OBSERVED_SURROGATE"
    internal_formula_claim: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fit_surrogate(
    rows: list[dict[str, float]],
    *,
    metric: str,
    inputs: list[str],
    model: str = "ridge",
    test_fraction: float = 0.25,
    seed: int = 17,
) -> SurrogateReport:
    if model not in _MODEL_NAMES:
        raise ValueError(f"model must be one of {sorted(_MODEL_NAMES)}")
    if len(rows) < 8:
        raise ValueError("At least 8 observations are required for a holdout surrogate.")
    if not inputs or any(any(key not in row for key in [*inputs, metric]) for row in rows):
        raise ValueError("Each row must contain the selected inputs and metric.")
    if not 0.1 <= test_fraction <= 0.4:
        raise ValueError("test_fraction must be between 0.1 and 0.4")
    try:
        from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.linear_model import LinearRegression, Ridge
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        from sklearn.model_selection import train_test_split
        from sklearn.tree import DecisionTreeRegressor
    except ImportError as exc:
        raise RuntimeError("Install the optional 'surrogate' extra to fit models.") from exc
    x = [[row[name] for name in inputs] for row in rows]
    y = [row[metric] for row in rows]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_fraction, random_state=seed
    )
    estimators = {
        "linear": LinearRegression(),
        "ridge": Ridge(alpha=1.0),
        "decision_tree": DecisionTreeRegressor(max_depth=4, random_state=seed),
        "random_forest": RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=seed),
        "gradient_boosting": GradientBoostingRegressor(random_state=seed),
        "gaussian_process": GaussianProcessRegressor(random_state=seed),
    }
    estimator = estimators[model]
    estimator.fit(x_train, y_train)
    predictions = estimator.predict(x_test)
    errors = [actual - predicted for actual, predicted in zip(y_test, predictions)]
    absolute = sorted(abs(error) for error in errors)
    bound_index = min(len(absolute) - 1, max(0, ceil(0.9 * len(absolute)) - 1))
    bound = absolute[bound_index]
    r2_value = float(r2_score(y_test, predictions)) if len(y_test) >= 2 else None
    return SurrogateReport(
        model=model,
        metric=metric,
        sample_count=len(rows),
        train_count=len(x_train),
        test_count=len(x_test),
        r2=r2_value,
        mae=float(mean_absolute_error(y_test, predictions)),
        rmse=sqrt(float(mean_squared_error(y_test, predictions))),
        empirical_interval=(-bound, bound),
    )
