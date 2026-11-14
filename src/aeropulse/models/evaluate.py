"""Métriques et choix du seuil de classification (FR-09, FR-10, ADR-0015).

Le seuil se choisit sur la **validation** uniquement (``best_f1_threshold``), jamais sur le test.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from sklearn.metrics import (
    average_precision_score,
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error,
    precision_recall_curve,
    roc_auc_score,
)

FloatArray = npt.NDArray[np.floating[Any]]


@dataclass(frozen=True)
class ClassificationMetrics:
    n: int
    prevalence: float
    pr_auc: float
    roc_auc: float
    threshold: float
    f1: float
    precision: float
    recall: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class RegressionMetrics:
    n: int
    mae: float
    rmse: float
    median_ae: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def best_f1_threshold(y_true: FloatArray, score: FloatArray) -> float:
    """Seuil maximisant le F1 (ADR-0015) ; à calculer sur la validation."""
    precision, recall, thresholds = precision_recall_curve(y_true, score)
    denom = precision[:-1] + recall[:-1]
    f1 = np.divide(
        2 * precision[:-1] * recall[:-1], denom, out=np.zeros_like(denom), where=denom > 0
    )
    if len(thresholds) == 0:
        return 0.5
    return float(thresholds[int(np.argmax(f1))])


def classification_metrics(
    y_true: FloatArray, score: FloatArray, threshold: float | None = None
) -> ClassificationMetrics:
    """Métriques de classification. ``threshold`` absent : seuil F1-optimal sur ces données."""
    thr = best_f1_threshold(y_true, score) if threshold is None else threshold
    pred = score >= thr
    tp = float(np.sum(pred & (y_true == 1)))
    precision = tp / float(np.sum(pred)) if pred.any() else 0.0
    recall = tp / float(np.sum(y_true == 1))
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
    constant = bool(np.all(score == score[0]))
    return ClassificationMetrics(
        n=len(y_true),
        prevalence=float(np.mean(y_true)),
        pr_auc=float(average_precision_score(y_true, score)),
        roc_auc=0.5 if constant else float(roc_auc_score(y_true, score)),
        threshold=thr,
        f1=f1,
        precision=precision,
        recall=recall,
    )


def regression_metrics(y_true: FloatArray, pred: FloatArray) -> RegressionMetrics:
    return RegressionMetrics(
        n=len(y_true),
        mae=float(mean_absolute_error(y_true, pred)),
        rmse=float(np.sqrt(mean_squared_error(y_true, pred))),
        median_ae=float(median_absolute_error(y_true, pred)),
    )
