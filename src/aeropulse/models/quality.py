"""Contrôle de qualité avant enregistrement d'un modèle de classification (D-22, AC-09).

Un modèle n'est enregistré que si **toutes** les conditions sont vraies ; sinon la liste des
échecs est renvoyée. Les seuils sont dans ``config`` (source unique).
"""

from __future__ import annotations

from dataclasses import dataclass

from aeropulse import config


@dataclass(frozen=True)
class QualityResult:
    passed: bool
    failures: tuple[str, ...]


def check_quality(
    *,
    pr_auc: float,
    baseline_pr_auc: float,
    roc_auc: float,
    mean_predicted: float,
    observed_rate: float,
    leakage_tests_passed: bool,
) -> QualityResult:
    """Évalue les quatre conditions de D-22 sur un même jeu d'évaluation."""
    failures: list[str] = []
    gain = pr_auc - baseline_pr_auc
    if gain < config.QUALITY_MIN_PR_AUC_GAIN:
        failures.append(
            f"gain de PR-AUC {gain:.3f} < {config.QUALITY_MIN_PR_AUC_GAIN} sur la baseline"
        )
    if roc_auc < config.QUALITY_MIN_ROC_AUC:
        failures.append(f"ROC-AUC {roc_auc:.3f} < {config.QUALITY_MIN_ROC_AUC}")
    gap = abs(mean_predicted - observed_rate)
    if gap > config.QUALITY_MAX_CALIBRATION_GAP:
        failures.append(f"écart de calibration {gap:.3f} > {config.QUALITY_MAX_CALIBRATION_GAP}")
    if not leakage_tests_passed:
        failures.append("tests de non-fuite en échec")
    return QualityResult(not failures, tuple(failures))
