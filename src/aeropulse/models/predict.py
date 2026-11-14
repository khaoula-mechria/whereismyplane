"""Prédicteur partagé entre évaluation et service (T4.9, R-18).

Charge l'export ``release`` et applique **le même code de variables** que l'entraînement
(``train.features`` / ``train._as_xgb``). Renvoie probabilité, décision au seuil figé, version du
modèle et explications SHAP (influence, pas cause).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import xgboost as xgb

from aeropulse import config
from aeropulse.models import explain
from aeropulse.models.train import _as_xgb, features


class Predictor:
    def __init__(self, release_dir: Path) -> None:
        self.manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
        meta = json.loads((release_dir / "meta.json").read_text(encoding="utf-8"))
        if meta["feature_columns"] != list(config.FEATURE_COLUMNS):
            raise ValueError("le contrat de variables a changé depuis l'entraînement du modèle")
        self.threshold = float(self.manifest["threshold"])
        self.model_version = str(self.manifest["model_version"])
        self._dtypes = {c: pd.CategoricalDtype(v) for c, v in meta["categories"].items()}
        self._clf = xgb.XGBClassifier()
        self._clf.load_model(release_dir / "classifier.json")

    def _matrix(self, rows: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in config.FEATURE_COLUMNS if c not in rows.columns]
        if missing:
            raise ValueError(f"variables manquantes : {missing}")
        return _as_xgb(features(rows), self._dtypes)

    def predict(self, rows: pd.DataFrame) -> pd.DataFrame:
        """Probabilité de retard > 15 min et décision au seuil choisi sur la validation."""
        proba = self._clf.predict_proba(self._matrix(rows))[:, 1]
        return pd.DataFrame(
            {
                "delay_probability": proba,
                "is_delayed_predicted": proba >= self.threshold,
                "threshold": self.threshold,
                "model_version": self.model_version,
            },
            index=rows.index,
        )

    def explain(self, rows: pd.DataFrame, top_k: int = 5) -> list[dict[str, Any]]:
        """Explications locales (au moins 3 contributions, AC-08), une par ligne."""
        x = self._matrix(rows)
        contrib = explain.contributions(self._clf, x)
        return [
            explain.local_explanation(contrib[i], x.iloc[i], top_k=top_k) for i in range(len(x))
        ]
