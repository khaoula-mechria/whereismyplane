from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from aeropulse import config
from aeropulse.models import train


def _ml(n: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    df = pd.DataFrame(
        {
            "carrier": rng.choice(["AA", "DL", "B6"], n),
            "origin": rng.choice(["JFK", "LGA", "EWR"], n),
            "destination": rng.choice(["LAX", "ATL", "ORD"], n),
            "route": rng.choice(["JFK-LAX", "LGA-ATL"], n),
            "season": rng.choice(["winter", "summer"], n),
        }
    )
    for col in config.NUMERIC_FEATURES:
        df[col] = rng.normal(size=n)
    df.loc[::17, "visibility_m"] = np.nan
    signal = df["visibility_m"].fillna(0) + rng.normal(scale=0.5, size=n)
    df["dep_delay"] = signal * 10
    df["is_delayed"] = (df["dep_delay"] > 5).astype("boolean")
    df["split"] = ["train"] * (n // 3) + ["validation"] * (n // 3) + ["test"] * (n - 2 * (n // 3))
    return df


def _close(a: dict[str, dict[str, float]], b: dict[str, dict[str, float]]) -> bool:
    """Égalité à 0,1 % près (XGBoost multi-thread n'est pas strictement déterministe)."""
    return a.keys() == b.keys() and all(
        np.isclose(a[m][k], b[m][k], rtol=1e-3, atol=1e-9) for m in a for k in a[m]
    )


def test_feature_matrix_follows_contract() -> None:
    x = train.features(_ml(30))
    assert list(x.columns) == list(config.FEATURE_COLUMNS)
    assert config.forbidden_columns_in(x.columns) == []


def test_run_produces_metrics_and_never_reads_test(tmp_path: Path) -> None:
    ml = _ml()
    path = tmp_path / "ml.parquet"
    ml.to_parquet(path, index=False)
    small = train.Settings(rf_trees=10, rf_max_depth=5, rf_min_samples_leaf=5, xgb_trees=20)
    r1 = train.run(path, small)
    assert set(r1["classification"]) == {"logistic_regression", "random_forest", "xgboost"}
    assert set(r1["regression"]) >= {"linear_regression", "random_forest", "xgboost_absolute_error"}
    assert r1["classification"]["xgboost"]["pr_auc"] > r1["classification"]["xgboost"]["prevalence"]
    ml.loc[ml["split"] == "test", "dep_delay"] = 1e6  # étiquettes du test altérées
    ml.loc[ml["split"] == "test", "is_delayed"] = True
    alt = tmp_path / "alt.parquet"
    ml.to_parquet(alt, index=False)
    r2 = train.run(alt, small)
    for key in ("classification", "regression"):
        assert _close(r1[key], r2[key])
