from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aeropulse.models import baselines, evaluate


def test_best_f1_threshold_separable() -> None:
    y = np.array([0, 0, 0, 1, 1, 1], dtype="float64")
    score = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    thr = evaluate.best_f1_threshold(y, score)
    m = evaluate.classification_metrics(y, score, threshold=thr)
    assert m.f1 == 1.0 and m.pr_auc == 1.0 and m.roc_auc == 1.0


def test_constant_score_has_prevalence_pr_auc_and_half_roc() -> None:
    y = np.array([0, 1, 0, 0], dtype="float64")
    m = evaluate.classification_metrics(y, np.full(4, 0.25), threshold=0.0)
    assert m.pr_auc == pytest.approx(0.25) and m.roc_auc == 0.5 and m.recall == 1.0


def test_regression_metrics() -> None:
    m = evaluate.regression_metrics(np.array([0.0, 10.0]), np.array([0.0, 0.0]))
    assert m.mae == 5.0 and m.rmse == pytest.approx(np.sqrt(50.0))


def test_baselines_never_read_test_labels(tmp_path: Path) -> None:
    rng = np.random.default_rng(0)
    n = 300
    split = np.array(["train"] * 100 + ["validation"] * 100 + ["test"] * 100)
    ml = pd.DataFrame(
        {
            "origin": rng.choice(["JFK", "LGA"], n),
            "departure_hour": rng.integers(6, 10, n),
            "is_delayed": pd.array(rng.random(n) < 0.2, dtype="boolean"),
            "dep_delay": rng.normal(5, 20, n),
            "split": split,
        }
    )
    base = tmp_path / "a.parquet"
    ml.to_parquet(base, index=False)
    r1 = baselines.run(base)
    # Modifier les étiquettes du test ne doit rien changer aux résultats.
    ml.loc[ml["split"] == "test", "dep_delay"] = 1e6
    ml.loc[ml["split"] == "test", "is_delayed"] = True
    alt = tmp_path / "b.parquet"
    ml.to_parquet(alt, index=False)
    assert baselines.run(alt) == r1
    assert r1["evaluated_on"] == "validation"
