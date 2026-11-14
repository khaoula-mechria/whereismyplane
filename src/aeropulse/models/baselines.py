"""Baselines (T4.1) : références chiffrées que les modèles doivent battre (AC-05, AC-06).

Ajustées sur l'**entraînement**, évaluées sur la **validation**. Le jeu de test n'est pas lu
(il ne sert qu'une fois, T4.6). Commande : ``uv run python -m aeropulse.models.baselines``.
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

from aeropulse import config
from aeropulse.features.split import select_split
from aeropulse.models import evaluate

GROUP = ["origin", "departure_hour"]


def _by_group(frame: pd.DataFrame, table: pd.Series, fallback: float) -> np.ndarray[Any, Any]:
    idx = pd.MultiIndex.from_frame(frame[GROUP])
    return table.reindex(idx).fillna(fallback).to_numpy(dtype="float64")


def run(ml_path: Path) -> dict[str, Any]:
    ml = pd.read_parquet(ml_path)
    train = select_split(ml, "train")
    val = select_split(ml, "validation")  # le test n'est jamais sélectionné ici
    y_cls_tr = train[config.TARGET_CLASSIFICATION].astype(float)
    y_cls = val[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
    y_reg = val[config.TARGET_REGRESSION].to_numpy(dtype="float64")

    prevalence = float(y_cls_tr.mean())
    rate = train.assign(_y=y_cls_tr).groupby(GROUP)["_y"].mean()
    score_heur = _by_group(val, rate, prevalence)
    score_const = np.full(len(val), prevalence)

    thr = evaluate.best_f1_threshold(y_cls, score_heur)
    classification = {
        "prevalence_constant": evaluate.classification_metrics(y_cls, score_const, threshold=0.0),
        "origin_hour_rate": evaluate.classification_metrics(y_cls, score_heur, threshold=thr),
    }

    med = float(train[config.TARGET_REGRESSION].median())
    mean = float(train[config.TARGET_REGRESSION].mean())
    med_table = train.groupby(GROUP)[config.TARGET_REGRESSION].median()
    regression = {
        "global_median": evaluate.regression_metrics(y_reg, np.full(len(val), med)),
        "global_mean": evaluate.regression_metrics(y_reg, np.full(len(val), mean)),
        "origin_hour_median": evaluate.regression_metrics(y_reg, _by_group(val, med_table, med)),
    }
    return {
        "evaluated_on": "validation",
        "fitted_on": "train",
        "train_prevalence": prevalence,
        "train_median_delay_min": med,
        "train_mean_delay_min": mean,
        "classification": {k: v.as_dict() for k, v in classification.items()},
        "regression": {k: v.as_dict() for k, v in regression.items()},
    }


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ml-dataset", type=Path, default=Path("data/ml/ml_dataset.parquet"))
    p.add_argument("--out", type=Path, default=Path("data/ml/baselines.json"))
    args = p.parse_args(argv)
    report = run(args.ml_dataset)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
