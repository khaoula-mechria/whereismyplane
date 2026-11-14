"""SHAP global et local (T4.7, FR-11, AC-08).

Contributions SHAP exactes de XGBoost (``pred_contribs``) en log-cotes pour la classification.
Ce sont des **influences sur le modèle, pas des causes**. Calcul sur la validation ; le jeu de
test n'est jamais lu ici. Commande : ``uv run python -m aeropulse.models.explain``.
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
from aeropulse.models.train import _as_xgb, features

DISCLAIMER = "Influence sur la prédiction du modèle, pas une cause."
MIN_LOCAL_CONTRIBUTIONS = 3


def load_classifier(model_dir: Path) -> tuple[xgb.XGBClassifier, dict[str, pd.CategoricalDtype]]:
    meta = json.loads((model_dir / "meta.json").read_text(encoding="utf-8"))
    clf = xgb.XGBClassifier()
    clf.load_model(model_dir / "classifier.json")
    dtypes = {c: pd.CategoricalDtype(v) for c, v in meta["categories"].items()}
    return clf, dtypes


def contributions(clf: xgb.XGBClassifier, x: pd.DataFrame) -> np.ndarray[Any, Any]:
    """Contributions SHAP (n, variables) en log-cotes ; dernière colonne = base."""
    dmat = xgb.DMatrix(x, enable_categorical=True)
    out: np.ndarray[Any, Any] = clf.get_booster().predict(dmat, pred_contribs=True)
    return out


def global_importance(contrib: np.ndarray[Any, Any]) -> list[dict[str, float | str]]:
    """Importance globale = contribution absolue moyenne par variable, décroissante."""
    mean_abs = np.abs(contrib[:, :-1]).mean(axis=0)
    ranked = sorted(
        zip(config.FEATURE_COLUMNS, mean_abs.tolist(), strict=True), key=lambda t: -t[1]
    )
    return [{"feature": f, "mean_abs_shap": v} for f, v in ranked]


def local_explanation(
    contrib_row: np.ndarray[Any, Any], values: pd.Series, top_k: int = 5
) -> dict[str, Any]:
    """Les ``top_k`` variables qui poussent le plus la prédiction (jamais moins de 3, AC-08)."""
    k = max(top_k, MIN_LOCAL_CONTRIBUTIONS)
    order = np.argsort(-np.abs(contrib_row[:-1]))[:k]
    items = [
        {
            "feature": config.FEATURE_COLUMNS[i],
            "value": None
            if pd.isna(values.iloc[i])
            else values.iloc[i].item()
            if hasattr(values.iloc[i], "item")
            else str(values.iloc[i]),
            "shap": float(contrib_row[i]),
            "direction": "augmente le risque" if contrib_row[i] > 0 else "diminue le risque",
        }
        for i in order
    ]
    return {"contributions": items, "base_value": float(contrib_row[-1]), "disclaimer": DISCLAIMER}


def run(ml_path: Path, model_dir: Path, sample: int = 30000, seed: int = 42) -> dict[str, Any]:
    clf, dtypes = load_classifier(model_dir)
    ml = pd.read_parquet(ml_path)
    val = select_split(ml, "validation")  # le test n'est jamais sélectionné ici
    val = val.sample(n=min(sample, len(val)), random_state=seed)
    x = _as_xgb(features(val), dtypes)
    contrib = contributions(clf, x)
    # Cohérence : somme des contributions = marge (log-cotes) du modèle.
    margin = clf.get_booster().predict(xgb.DMatrix(x, enable_categorical=True), output_margin=True)
    max_gap = float(np.max(np.abs(contrib.sum(axis=1) - margin)))
    return {
        "evaluated_on": "validation (échantillon)",
        "n": len(x),
        "additivity_max_gap": max_gap,
        "global_importance": global_importance(contrib),
        "example": local_explanation(contrib[0], x.iloc[0]),
        "disclaimer": DISCLAIMER,
    }


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ml-dataset", type=Path, default=Path("data/ml/ml_dataset.parquet"))
    p.add_argument("--model-dir", type=Path, default=Path("data/ml/models"))
    p.add_argument("--out", type=Path, default=Path("data/ml/models/shap_report.json"))
    args = p.parse_args(argv)
    report = run(args.ml_dataset, args.model_dir)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
