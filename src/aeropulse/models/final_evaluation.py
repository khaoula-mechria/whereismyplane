"""Évaluation finale unique sur le jeu de test (T4.6, AC-05, AC-06, AC-07).

Charge les artefacts **figés** de ``aeropulse.models.final`` (modèles, seuil choisi sur la
validation) et les évalue sur le test, **une seule fois** : un fichier de verrou écrit avec le
rapport empêche toute seconde exécution. Aucun réglage ni aucun seuil n'est recalculé ici.
Commande : ``uv run python -m aeropulse.models.final_evaluation --final-evaluation``.
"""

from __future__ import annotations

import argparse
import hashlib
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
from aeropulse.models.train import _as_xgb, features

REPORT_NAME = "test_evaluation.json"
GROUP = ["origin", "departure_hour"]
BOOTSTRAP = 200
ARTIFACTS = ("classifier.json", "regressor.json", "meta.json", "validation_report.json")


class AlreadyEvaluatedError(RuntimeError):
    """Le jeu de test a déjà servi : une seconde évaluation serait biaisée."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _by_group(frame: pd.DataFrame, table: pd.Series, fallback: float) -> np.ndarray[Any, Any]:
    idx = pd.MultiIndex.from_frame(frame[GROUP])
    return table.reindex(idx).fillna(fallback).to_numpy(dtype="float64")


def _bootstrap_ci(
    metric: Any, arrays: Sequence[np.ndarray[Any, Any]], seed: int = 42
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(arrays[0])
    values = []
    for _ in range(BOOTSTRAP):
        idx = rng.integers(0, n, n)
        values.append(metric(*[a[idx] for a in arrays]))
    lo, hi = np.percentile(values, [2.5, 97.5])
    return float(lo), float(hi)


def _segments(test: pd.DataFrame, p: np.ndarray[Any, Any], pred: np.ndarray[Any, Any]) -> Any:
    frame = test.assign(p=p, pred=pred, y=test[config.TARGET_CLASSIFICATION].astype(float))
    frame["abs_err"] = (frame[config.TARGET_REGRESSION] - frame["pred"]).abs()
    frame["hour_band"] = pd.cut(
        frame["departure_hour"],
        [-1, 5, 9, 13, 17, 21, 24],
        labels=["0-5", "6-9", "10-13", "14-17", "18-21", "22-23"],
    )
    frame["month_name"] = pd.to_datetime(frame["flight_date"]).dt.to_period("M").astype(str)
    out: dict[str, list[dict[str, Any]]] = {}
    for key in ("origin", "hour_band", "month_name"):
        rows = []
        for name, g in frame.groupby(key, observed=True):
            if len(g) < config.MIN_SAMPLE_SIZE:
                continue
            rows.append(
                {
                    "segment": str(name),
                    "n": len(g),
                    "delay_rate": float(g["y"].mean()),
                    "mean_predicted": float(g["p"].mean()),
                    "mae": float(g["abs_err"].mean()),
                }
            )
        out[key] = rows
    top = frame["carrier"].value_counts().head(8).index
    out["carrier_top8"] = [
        {
            "segment": str(c),
            "n": int(len(g)),
            "delay_rate": float(g["y"].mean()),
            "mean_predicted": float(g["p"].mean()),
            "mae": float(g["abs_err"].mean()),
        }
        for c, g in frame[frame["carrier"].isin(top)].groupby("carrier")
    ]
    return out


def run(ml_path: Path, model_dir: Path, *, final_evaluation: bool = False) -> dict[str, Any]:
    if not final_evaluation:
        raise PermissionError("évaluation finale : passer final_evaluation=True (usage unique)")
    report_path = model_dir / REPORT_NAME
    if report_path.exists():
        raise AlreadyEvaluatedError(f"{report_path} existe : le test a déjà servi")
    meta = json.loads((model_dir / "meta.json").read_text(encoding="utf-8"))
    threshold = float(meta["threshold"])
    hashes = {name: _sha256(model_dir / name) for name in ARTIFACTS}

    ml = pd.read_parquet(ml_path)
    train = select_split(ml, "train")
    val = select_split(ml, "validation")
    test = select_split(ml, "test", final_evaluation=True)  # seul endroit qui lit le test
    dtypes = {c: pd.CategoricalDtype(v) for c, v in meta["categories"].items()}
    x_test = _as_xgb(features(test), dtypes)
    y_cls = test[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
    y_reg = test[config.TARGET_REGRESSION].to_numpy(dtype="float64")

    clf = xgb.XGBClassifier()
    clf.load_model(model_dir / "classifier.json")
    reg = xgb.XGBRegressor()
    reg.load_model(model_dir / "regressor.json")
    p = clf.predict_proba(x_test)[:, 1]
    pred = reg.predict(x_test)

    # Baselines ajustées sur l'entraînement ; leur seuil est choisi sur la validation.
    y_tr = train[config.TARGET_CLASSIFICATION].astype(float)
    prevalence = float(y_tr.mean())
    rate = train.assign(_y=y_tr).groupby(GROUP)["_y"].mean()
    y_val = val[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
    base_thr = evaluate.best_f1_threshold(y_val, _by_group(val, rate, prevalence))
    base_score = _by_group(test, rate, prevalence)
    med = float(train[config.TARGET_REGRESSION].median())
    med_table = train.groupby(GROUP)[config.TARGET_REGRESSION].median()

    cls = evaluate.classification_metrics(y_cls, p, threshold)
    base_cls = evaluate.classification_metrics(y_cls, base_score, base_thr)
    pr_ci = _bootstrap_ci(
        lambda y, s: evaluate.classification_metrics(y, s, threshold).pr_auc, [y_cls, p]
    )
    reg_m = evaluate.regression_metrics(y_reg, pred)
    base_reg = {
        "global_median": evaluate.regression_metrics(y_reg, np.full(len(test), med)),
        "origin_hour_median": evaluate.regression_metrics(y_reg, _by_group(test, med_table, med)),
    }
    mae_ci = _bootstrap_ci(lambda y, q: float(np.mean(np.abs(y - q))), [y_reg, pred])
    best_base_mae = min(m.mae for m in base_reg.values())
    best_base_pr = base_cls.pr_auc

    report: dict[str, Any] = {
        "evaluated_on": "test",
        "period": f"{config.TEST_START} → {config.TEST_END}",
        "n": len(test),
        "artifact_sha256": hashes,
        "threshold_from_validation": threshold,
        "classification": {
            "model": cls.as_dict(),
            "pr_auc_ci95": list(pr_ci),
            "brier": float(np.mean((p - y_cls) ** 2)),
            "baseline_origin_hour_rate": base_cls.as_dict(),
            "prevalence_pr_auc": float(y_cls.mean()),
            "beats_baseline_pr_auc": bool(cls.pr_auc > best_base_pr),
            "mean_predicted": float(p.mean()),
            "observed_rate": float(y_cls.mean()),
        },
        "regression": {
            "model": reg_m.as_dict(),
            "mae_ci95": list(mae_ci),
            "baselines": {k: v.as_dict() for k, v in base_reg.items()},
            "beats_baseline_mae": bool(reg_m.mae < best_base_mae),
        },
        "segments": _segments(test, p, pred),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")  # verrou + rapport
    return report


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ml-dataset", type=Path, default=Path("data/ml/ml_dataset.parquet"))
    p.add_argument("--model-dir", type=Path, default=Path("data/ml/models"))
    p.add_argument("--final-evaluation", action="store_true", help="usage unique du jeu de test")
    args = p.parse_args(argv)
    report = run(args.ml_dataset, args.model_dir, final_evaluation=args.final_evaluation)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
