"""Modèles figés et rapport de validation (T4.5, T4.9 partiel).

Entraîne les deux modèles retenus avec ``tuned_params.json`` sur l'**entraînement** seul, choisit
le seuil F1 sur la **validation** (ADR-0015), calcule les métriques complètes et sauvegarde les
artefacts. Le jeu de test n'est jamais lu ici : l'évaluation finale (T4.6) charge ces artefacts
figés. Commande : ``uv run python -m aeropulse.models.final``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

from aeropulse import config
from aeropulse.features.split import select_split
from aeropulse.models import evaluate
from aeropulse.models.train import _as_xgb, _categorical_dtypes, features

PARAMS_PATH = Path(__file__).with_name("tuned_params.json")
THRESHOLD_GRID = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50)
CALIBRATION_BINS = 10


def _fixed(params: dict[str, Any], seed: int) -> dict[str, Any]:
    out = {k: v for k, v in params.items() if k != "note"}
    out.update(tree_method="hist", enable_categorical=True, n_jobs=-1, random_state=seed)
    return out


def calibration_table(y: np.ndarray[Any, Any], p: np.ndarray[Any, Any]) -> list[dict[str, float]]:
    """Probabilité moyenne prédite vs fréquence observée, par déciles de probabilité."""
    frame = pd.DataFrame({"y": y, "p": p})
    frame["bin"] = pd.qcut(frame["p"], CALIBRATION_BINS, duplicates="drop")
    grouped = frame.groupby("bin", observed=True).agg(
        n=("y", "size"), pred=("p", "mean"), obs=("y", "mean")
    )
    return [
        {"n": int(n), "mean_predicted": float(pred), "observed_rate": float(obs)}
        for n, pred, obs in zip(
            grouped["n"].tolist(), grouped["pred"].tolist(), grouped["obs"].tolist(), strict=True
        )
    ]


def threshold_table(y: np.ndarray[Any, Any], p: np.ndarray[Any, Any]) -> list[dict[str, float]]:
    rows = []
    for t in THRESHOLD_GRID:
        m = evaluate.classification_metrics(y, p, threshold=t)
        rows.append({"threshold": t, "precision": m.precision, "recall": m.recall, "f1": m.f1})
    return rows


def run(ml_path: Path, out_dir: Path, seed: int = 42) -> dict[str, Any]:
    params = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
    ml = pd.read_parquet(ml_path)
    train = select_split(ml, "train")
    val = select_split(ml, "validation")  # le test n'est jamais sélectionné ici
    dtypes = _categorical_dtypes(train)
    x_tr, x_val = _as_xgb(features(train), dtypes), _as_xgb(features(val), dtypes)
    y_cls_tr = train[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
    y_cls = val[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
    y_reg_tr = train[config.TARGET_REGRESSION].to_numpy(dtype="float64")
    y_reg = val[config.TARGET_REGRESSION].to_numpy(dtype="float64")

    clf = xgb.XGBClassifier(eval_metric="aucpr", **_fixed(params["classification"], seed))
    clf.fit(x_tr, y_cls_tr, verbose=False)
    reg = xgb.XGBRegressor(**_fixed(params["regression"], seed))
    reg.fit(x_tr, y_reg_tr, verbose=False)

    p_val = clf.predict_proba(x_val)[:, 1]
    threshold = evaluate.best_f1_threshold(y_cls, p_val)  # choisi sur la validation (ADR-0015)
    cls = evaluate.classification_metrics(y_cls, p_val, threshold)
    reg_pred = reg.predict(x_val)

    out_dir.mkdir(parents=True, exist_ok=True)
    clf.save_model(out_dir / "classifier.json")
    reg.save_model(out_dir / "regressor.json")
    meta = {
        "feature_columns": list(config.FEATURE_COLUMNS),
        "categories": {c: list(d.categories) for c, d in dtypes.items()},
        "threshold": threshold,
        "threshold_chosen_on": "validation (F1 maximal, ADR-0015)",
        "params": params,
        "trained_on": {
            "start": str(config.TRAIN_START),
            "end": str(config.TRAIN_END),
            "n": len(train),
        },
        "horizon_hours": config.PREDICTION_HORIZON.total_seconds() / 3600,
        "delay_threshold_minutes": config.DELAY_THRESHOLD_MINUTES,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    brier = float(np.mean((p_val - y_cls) ** 2))
    report = {
        "evaluated_on": "validation",
        "classification": {
            **cls.as_dict(),
            "brier": brier,
            "brier_reference_prevalence": float(np.mean((y_cls.mean() - y_cls) ** 2)),
            "thresholds": threshold_table(y_cls, p_val),
            "calibration": calibration_table(y_cls, p_val),
        },
        "regression": evaluate.regression_metrics(y_reg, reg_pred).as_dict(),
    }
    (out_dir / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ml-dataset", type=Path, default=Path("data/ml/ml_dataset.parquet"))
    p.add_argument("--out-dir", type=Path, default=Path("data/ml/models"))
    args = p.parse_args(argv)
    print(json.dumps(run(args.ml_dataset, args.out_dir), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
