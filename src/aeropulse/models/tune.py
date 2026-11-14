"""Réglage des hyperparamètres XGBoost sur la validation (T4.4).

Recherche aléatoire à graine fixe, ajustement sur l'**entraînement**, sélection sur la
**validation** (PR-AUC pour la classification, MAE pour la régression). Le jeu de test n'est
jamais lu. Les métriques de validation des meilleurs essais sont donc légèrement optimistes.
Commande : ``uv run python -m aeropulse.models.tune``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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

SPACE: dict[str, list[float | int]] = {
    "max_depth": [4, 6, 8, 10],
    "learning_rate": [0.03, 0.05, 0.1],
    "min_child_weight": [1, 5, 20, 50],
    "subsample": [0.7, 0.85, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0],
    "reg_lambda": [1.0, 5.0, 20.0],
}
IMBALANCE_WEIGHTS = [1.0, 2.0, 4.0]  # scale_pos_weight, classification uniquement
MAX_TREES = 1000
EARLY_STOPPING = 30


def sample_params(rng: np.random.Generator, *, classification: bool) -> dict[str, Any]:
    params: dict[str, Any] = {k: v[int(rng.integers(len(v)))] for k, v in SPACE.items()}
    if classification:
        params["scale_pos_weight"] = IMBALANCE_WEIGHTS[int(rng.integers(len(IMBALANCE_WEIGHTS)))]
    return params


def run(
    ml_path: Path, trials: int = 12, seed: int = 42, max_trees: int = MAX_TREES
) -> dict[str, Any]:
    ml = pd.read_parquet(ml_path)
    train = select_split(ml, "train")
    val = select_split(ml, "validation")  # le test n'est jamais sélectionné ici
    dtypes = _categorical_dtypes(train)
    x_tr, x_val = _as_xgb(features(train), dtypes), _as_xgb(features(val), dtypes)
    y_cls_tr = train[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
    y_cls = val[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
    y_reg_tr = train[config.TARGET_REGRESSION].to_numpy(dtype="float64")
    y_reg = val[config.TARGET_REGRESSION].to_numpy(dtype="float64")
    common = {
        "n_estimators": max_trees,
        "tree_method": "hist",
        "enable_categorical": True,
        "early_stopping_rounds": EARLY_STOPPING,
        "n_jobs": -1,
        "random_state": seed,
    }
    out: dict[str, Any] = {"evaluated_on": "validation", "fitted_on": "train", "trials": trials}
    rng = np.random.default_rng(seed)
    for task in ("classification", "regression"):
        log: list[dict[str, Any]] = []
        for i in range(trials):
            params = sample_params(rng, classification=task == "classification")
            start = time.perf_counter()
            if task == "classification":
                model = xgb.XGBClassifier(eval_metric="aucpr", **common, **params)
                model.fit(x_tr, y_cls_tr, eval_set=[(x_val, y_cls)], verbose=False)
                score = model.predict_proba(x_val)[:, 1]
                metric = evaluate.classification_metrics(y_cls, score)
                value = metric.pr_auc
            else:
                model = xgb.XGBRegressor(
                    objective="reg:absoluteerror", eval_metric="mae", **common, **params
                )
                model.fit(x_tr, y_reg_tr, eval_set=[(x_val, y_reg)], verbose=False)
                value = evaluate.regression_metrics(y_reg, model.predict(x_val)).mae
            log.append(
                {
                    "params": params,
                    "n_trees": int(model.best_iteration) + 1,
                    "value": float(value),
                    "seconds": round(time.perf_counter() - start, 1),
                }
            )
            print(f"{task} {i + 1}/{trials}: {value:.4f} {params}", flush=True)
        best = (max if task == "classification" else min)(log, key=lambda t: t["value"])
        out[task] = {
            "criterion": "pr_auc (max)" if task == "classification" else "mae (min)",
            "best": best,
            "log": log,
        }
    return out


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ml-dataset", type=Path, default=Path("data/ml/ml_dataset.parquet"))
    p.add_argument("--out", type=Path, default=Path("data/ml/tuning.json"))
    p.add_argument("--trials", type=int, default=12)
    args = p.parse_args(argv)
    report = run(args.ml_dataset, trials=args.trials)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
