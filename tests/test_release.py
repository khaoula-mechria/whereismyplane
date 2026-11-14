from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import xgboost as xgb

from aeropulse import config
from aeropulse.models import final, predict, quality, release
from aeropulse.models.train import _as_xgb, features
from test_train import _ml


def test_quality_gate_passes_measured_values_and_fails_degraded() -> None:
    ok = quality.check_quality(
        pr_auc=0.415,
        baseline_pr_auc=0.309,
        roc_auc=0.719,
        mean_predicted=0.225,
        observed_rate=0.213,
        leakage_tests_passed=True,
    )
    assert ok.passed and ok.failures == ()
    bad = quality.check_quality(
        pr_auc=0.33,
        baseline_pr_auc=0.309,
        roc_auc=0.60,
        mean_predicted=0.30,
        observed_rate=0.21,
        leakage_tests_passed=False,
    )
    assert not bad.passed and len(bad.failures) == 4


def test_release_drops_regression_and_predictor_matches_training_path(tmp_path: Path) -> None:
    ml = _ml()
    path = tmp_path / "ml.parquet"
    ml.to_parquet(path, index=False)
    final.run(path, tmp_path / "m")
    manifest = release.export_release(tmp_path / "m", tmp_path / "rel")
    assert not (tmp_path / "rel" / "regressor.json").exists()
    meta = json.loads((tmp_path / "rel" / "meta.json").read_text(encoding="utf-8"))
    assert "regression" not in meta["params"] and manifest["model_version"].startswith("clf-")

    pred = predict.Predictor(tmp_path / "rel")
    rows = ml[ml["split"] == "validation"].head(40)
    out = pred.predict(rows)
    # Parité avec le chemin d'entraînement : même matrice, même modèle.
    clf = xgb.XGBClassifier()
    clf.load_model(tmp_path / "m" / "classifier.json")
    dtypes = {c: pd.CategoricalDtype(v) for c, v in meta["categories"].items()}
    expected = clf.predict_proba(_as_xgb(features(rows), dtypes))[:, 1]
    assert out["delay_probability"].to_numpy() == pytest.approx(expected)
    assert (out["is_delayed_predicted"] == (out["delay_probability"] >= pred.threshold)).all()
    explanation = pred.explain(rows.head(2))
    assert len(explanation) == 2 and len(explanation[0]["contributions"]) >= 3
    with pytest.raises(ValueError):
        pred.predict(rows.drop(columns=[config.FEATURE_COLUMNS[0]]))
