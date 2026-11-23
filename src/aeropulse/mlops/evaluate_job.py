"""Étape « Evaluate » du pipeline SageMaker (Processing) : contrôle de qualité D-22.

Charge le bundle produit par l'entraînement (vérifié par empreinte), le **même prédicteur que la
Lambda** (``models.predict.Predictor``), et calcule sur la **validation** : PR-AUC, ROC-AUC,
écart de calibration, gain sur la baseline aéroport × heure. Les tests de non-fuite
(``tests/test_leakage.py``, copiés dans l'image) sont exécutés ici. ``check_quality`` (seuils dans
``config``) décide ; l'étape « QualityGate » du pipeline lit ``quality.passed_flag``.

Le jeu de **test n'est pas utilisé** : il a déjà servi une fois (T4.6, ADR-0004). Le seuil ayant
été choisi sur la validation, ces chiffres sont légèrement optimistes ; ils servent de garde-fou
automatique avant enregistrement, pas de mesure de performance finale.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from aeropulse import config
from aeropulse.features.split import select_split
from aeropulse.mlops import bundle
from aeropulse.models import baselines, evaluate, quality
from aeropulse.models.predict import Predictor

DEFAULT_CHECKS_DIR = Path(os.environ.get("AEROPULSE_CHECKS_DIR", "/var/task/checks"))


def leakage_tests_pass(checks_dir: Path) -> tuple[bool, str]:
    """Exécute les tests de non-fuite ; échec si le fichier est absent."""
    target = checks_dir / "test_leakage.py"
    if not target.is_file():
        return False, f"{target} absent"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    tail = (result.stdout + result.stderr).strip().splitlines()[-1:] or [""]
    return result.returncode == 0, tail[0]


def run(model_archive: Path, ml_dataset: Path, out: Path, checks_dir: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        info = bundle.extract_bundle(model_archive, Path(tmp) / "bundle")
        predictor = Predictor(info.release_dir)
        ml = pd.read_parquet(ml_dataset)
        val = select_split(ml, "validation")  # le test n'est jamais sélectionné ici
        y = val[config.TARGET_CLASSIFICATION].astype(float).to_numpy()
        p = predictor.predict(val)["delay_probability"].to_numpy(dtype="float64")
        metrics = evaluate.classification_metrics(y, p, threshold=predictor.threshold)
    base = baselines.run(ml_dataset)["classification"]["origin_hour_rate"]
    leak_ok, leak_summary = leakage_tests_pass(checks_dir)
    mean_predicted, observed = float(np.mean(p)), float(np.mean(y))
    result = quality.check_quality(
        pr_auc=metrics.pr_auc,
        baseline_pr_auc=float(base["pr_auc"]),
        roc_auc=metrics.roc_auc,
        mean_predicted=mean_predicted,
        observed_rate=observed,
        leakage_tests_passed=leak_ok,
    )
    report: dict[str, Any] = {
        "model_version": info.model_version,
        "evaluated_on": "validation",
        "test_set_used": False,
        "classification": metrics.as_dict(),
        "baseline_origin_hour": {"pr_auc": float(base["pr_auc"])},
        "calibration": {"mean_predicted": mean_predicted, "observed_rate": observed},
        "leakage_tests": {"passed": leak_ok, "summary": leak_summary},
        "quality": {
            "passed": result.passed,
            "passed_flag": int(result.passed),
            "failures": list(result.failures),
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--model", type=Path, default=Path("/opt/ml/processing/input/model/model.tar.gz")
    )
    p.add_argument(
        "--ml-dataset", type=Path, default=Path("/opt/ml/processing/input/ml/ml_dataset.parquet")
    )
    p.add_argument(
        "--out", type=Path, default=Path("/opt/ml/processing/output/evaluation/evaluation.json")
    )
    p.add_argument("--checks-dir", type=Path, default=DEFAULT_CHECKS_DIR)
    args = p.parse_args(argv)
    report = run(args.model, args.ml_dataset, args.out, args.checks_dir)
    print(json.dumps(report, indent=2))
    return 0  # l'échec de qualité est décidé par l'étape Condition, pas par un code de sortie


if __name__ == "__main__":
    sys.exit(main())
