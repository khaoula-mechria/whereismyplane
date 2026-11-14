"""Entraînement de trois modèles par tâche (T4.2, T4.3, FR-08).

scikit-learn et XGBoost en local ; SageMaker seulement après l'estimation de coûts (G0).
Ajustement sur l'**entraînement**, évaluation sur la **validation** ; le jeu de test n'est jamais
lu ici (évaluation finale unique : T4.6). Commande : ``uv run python -m aeropulse.models.train``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from aeropulse import config
from aeropulse.features.split import select_split
from aeropulse.models import evaluate

CATEGORICAL = list(config.CATEGORICAL_FEATURES)
NUMERIC = list(config.NUMERIC_FEATURES)


@dataclass(frozen=True)
class Settings:
    """Hyperparamètres de départ (réglage fin : T4.4, sur la validation)."""

    rf_trees: int = 100
    rf_max_depth: int = 14
    rf_min_samples_leaf: int = 50
    xgb_trees: int = 600
    xgb_learning_rate: float = 0.08
    xgb_max_depth: int = 6
    xgb_early_stopping: int = 30
    random_state: int = 42


def features(df: pd.DataFrame) -> pd.DataFrame:
    """Matrice de variables dans l'ordre du contrat ``config.FEATURE_COLUMNS`` (rien d'autre)."""
    config.assert_no_forbidden_columns(config.FEATURE_COLUMNS)
    x = df[list(config.FEATURE_COLUMNS)].copy()
    for col in NUMERIC:
        x[col] = pd.to_numeric(x[col].astype("float64"), errors="coerce")
    return x


def _linear_pre() -> ColumnTransformer:
    numeric = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())])
    onehot = OneHotEncoder(handle_unknown="ignore", min_frequency=100)
    return ColumnTransformer([("num", numeric, NUMERIC), ("cat", onehot, CATEGORICAL)])


def _tree_pre() -> ColumnTransformer:
    ordinal = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    return ColumnTransformer(
        [("num", "passthrough", NUMERIC), ("cat", ordinal, CATEGORICAL)]
    )  # les NaN restent des NaN (gérés nativement par les forêts)


def _categorical_dtypes(train: pd.DataFrame) -> dict[str, pd.CategoricalDtype]:
    return {c: pd.CategoricalDtype(sorted(train[c].astype(str).unique())) for c in CATEGORICAL}


def _as_xgb(x: pd.DataFrame, dtypes: dict[str, pd.CategoricalDtype]) -> pd.DataFrame:
    out = x.copy()
    for col, dtype in dtypes.items():
        values = out[col].astype(str)
        # catégorie inconnue de l'entraînement -> manquante (gérée nativement par XGBoost)
        out[col] = pd.Categorical(values.where(values.isin(dtype.categories)), dtype=dtype)
    return out


def _timed(name: str, fn: Any) -> tuple[Any, float]:
    start = time.perf_counter()
    result = fn()
    print(f"  {name} : {time.perf_counter() - start:.0f} s", flush=True)
    return result, time.perf_counter() - start


def run(
    ml_path: Path, settings: Settings | None = None, sample: int | None = None
) -> dict[str, Any]:
    settings = settings or Settings()
    ml = pd.read_parquet(ml_path)
    train = select_split(ml, "train")
    val = select_split(ml, "validation")  # le test n'est jamais sélectionné ici
    if sample is not None:
        train = train.sample(n=min(sample, len(train)), random_state=settings.random_state)
    x_tr, x_val = features(train), features(val)
    y_cls_tr = train[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
    y_cls = val[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
    y_reg_tr = train[config.TARGET_REGRESSION].to_numpy(dtype="float64")
    y_reg = val[config.TARGET_REGRESSION].to_numpy(dtype="float64")
    seed = settings.random_state
    dtypes = _categorical_dtypes(train)
    xx_tr, xx_val = _as_xgb(x_tr, dtypes), _as_xgb(x_val, dtypes)
    cls_scores: dict[str, np.ndarray[Any, Any]] = {}
    reg_preds: dict[str, np.ndarray[Any, Any]] = {}
    seconds: dict[str, float] = {}

    def fit_predict(name: str, build: Any, scores: dict[str, Any], fn: Any) -> None:
        task = "classification" if scores is cls_scores else "regression"
        model, secs = _timed(f"{task}/{name}", build)
        scores[name] = fn(model)
        seconds[f"{task}/{name}"] = round(secs, 1)

    # --- Classification ---
    fit_predict(
        "logistic_regression",
        lambda: Pipeline(
            [("pre", _linear_pre()), ("m", LogisticRegression(max_iter=300, C=1.0))]
        ).fit(x_tr, y_cls_tr),
        cls_scores,
        lambda m: m.predict_proba(x_val)[:, 1],
    )
    fit_predict(
        "random_forest",
        lambda: Pipeline(
            [
                ("pre", _tree_pre()),
                (
                    "m",
                    RandomForestClassifier(
                        n_estimators=settings.rf_trees,
                        max_depth=settings.rf_max_depth,
                        min_samples_leaf=settings.rf_min_samples_leaf,
                        n_jobs=-1,
                        random_state=seed,
                    ),
                ),
            ]
        ).fit(x_tr, y_cls_tr),
        cls_scores,
        lambda m: m.predict_proba(x_val)[:, 1],
    )
    xgb_cls_params = {
        "n_estimators": settings.xgb_trees,
        "learning_rate": settings.xgb_learning_rate,
        "max_depth": settings.xgb_max_depth,
        "tree_method": "hist",
        "enable_categorical": True,
        "early_stopping_rounds": settings.xgb_early_stopping,
        "n_jobs": -1,
        "random_state": seed,
    }
    best_iters: dict[str, int] = {}

    def build_xgb_cls() -> Any:
        model = xgb.XGBClassifier(eval_metric="aucpr", **xgb_cls_params)
        model.fit(xx_tr, y_cls_tr, eval_set=[(xx_val, y_cls)], verbose=False)
        best_iters["xgboost_classifier"] = int(model.best_iteration)
        return model

    fit_predict("xgboost", build_xgb_cls, cls_scores, lambda m: m.predict_proba(xx_val)[:, 1])

    classification: dict[str, Any] = {}
    for name, score in cls_scores.items():
        threshold = evaluate.best_f1_threshold(y_cls, score)  # seuil choisi sur la validation
        classification[name] = evaluate.classification_metrics(y_cls, score, threshold).as_dict()

    # --- Régression ---
    fit_predict(
        "linear_regression",
        lambda: Pipeline([("pre", _linear_pre()), ("m", LinearRegression())]).fit(x_tr, y_reg_tr),
        reg_preds,
        lambda m: m.predict(x_val),
    )
    fit_predict(
        "random_forest",
        lambda: Pipeline(
            [
                ("pre", _tree_pre()),
                (
                    "m",
                    RandomForestRegressor(
                        n_estimators=settings.rf_trees,
                        max_depth=settings.rf_max_depth,
                        min_samples_leaf=settings.rf_min_samples_leaf,
                        n_jobs=-1,
                        random_state=seed,
                    ),
                ),
            ]
        ).fit(x_tr, y_reg_tr),
        reg_preds,
        lambda m: m.predict(x_val),
    )
    for name, objective, metric in (
        ("xgboost_squared_error", "reg:squarederror", "rmse"),
        ("xgboost_absolute_error", "reg:absoluteerror", "mae"),
    ):

        def build_xgb_reg(
            objective: str = objective, metric: str = metric, name: str = name
        ) -> Any:
            params = {k: v for k, v in xgb_cls_params.items()}
            model = xgb.XGBRegressor(objective=objective, eval_metric=metric, **params)
            model.fit(xx_tr, y_reg_tr, eval_set=[(xx_val, y_reg)], verbose=False)
            best_iters[name] = int(model.best_iteration)
            return model

        fit_predict(name, build_xgb_reg, reg_preds, lambda m: m.predict(xx_val))
    regression = {n: evaluate.regression_metrics(y_reg, p).as_dict() for n, p in reg_preds.items()}

    return {
        "evaluated_on": "validation",
        "fitted_on": "train",
        "n_train": len(train),
        "classification": classification,
        "regression": regression,
        "xgboost_best_iteration": best_iters,
        "fit_seconds": seconds,
    }


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ml-dataset", type=Path, default=Path("data/ml/ml_dataset.parquet"))
    p.add_argument("--out", type=Path, default=Path("data/ml/model_results.json"))
    p.add_argument("--sample", type=int, default=None, help="sous-échantillon d'entraînement")
    args = p.parse_args(argv)
    report = run(args.ml_dataset, sample=args.sample)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
