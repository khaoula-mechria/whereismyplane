"""Étape « Train » du pipeline SageMaker (Training) : modèle figé + bundle de service.

Conventions SageMaker : canaux d'entrée dans ``/opt/ml/input/data/<canal>``, tout ce qui est
écrit dans ``/opt/ml/model`` devient ``model.tar.gz``. Ici ``/opt/ml/model`` reçoit un **bundle**
complet (``release/``, ``serving/``, ``bundle.json``) plus ``reports/validation_report.json`` :
l'artefact enregistré dans le Model Registry est directement servable par la Lambda.

Réutilise ``models.final`` (entraînement sur l'entraînement seul, seuil F1 sur la validation,
ADR-0015 ; le test n'est jamais lu) et ``models.release`` (export versionné par empreinte).
Lancé par l'image avec l'argument ``train`` (convention SageMaker, voir ``entrypoint.sh``).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import traceback
from collections.abc import Sequence
from pathlib import Path

from aeropulse.mlops import bundle
from aeropulse.models import final, release

SM_INPUT = Path("/opt/ml/input/data")
SM_MODEL = Path("/opt/ml/model")
SM_FAILURE = Path("/opt/ml/output/failure")


def run(ml_dataset: Path, serving_dir: Path, model_dir: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        validation = final.run(ml_dataset, work / "models")
        manifest = release.export_release(work / "models", work / "release")
        info = bundle.stage_bundle(work / "release", serving_dir, model_dir)
        (model_dir / "reports").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            work / "models" / "validation_report.json",
            model_dir / "reports" / "validation_report.json",
        )
    bundle.verify_bundle(model_dir)  # même contrôle que la Lambda avant d'exposer l'artefact
    cls = validation["classification"]
    return {
        "model_version": manifest["model_version"],
        "threshold": manifest["threshold"],
        "validation_pr_auc": cls["pr_auc"],
        "validation_roc_auc": cls["roc_auc"],
        "serving_files": sorted(info["serving_files"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ml-dataset", type=Path, default=SM_INPUT / "ml" / "ml_dataset.parquet")
    p.add_argument("--serving-dir", type=Path, default=SM_INPUT / "serving")
    p.add_argument("--model-dir", type=Path, default=SM_MODEL)
    args = p.parse_args(argv)
    try:
        print(json.dumps(run(args.ml_dataset, args.serving_dir, args.model_dir), indent=2))
    except Exception:
        message = traceback.format_exc()
        print(message, file=sys.stderr)
        if SM_FAILURE.parent.exists():  # message d'échec affiché par SageMaker
            SM_FAILURE.write_text(message[-1024:], encoding="utf-8")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
