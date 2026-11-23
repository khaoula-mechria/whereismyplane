"""Étape « Prepare » du pipeline SageMaker (Processing) : données brutes -> jeu ML + tables.

Réutilise **sans le modifier** le code local testé : ``data.pipeline`` (validation, nettoyage,
météo ≤ T-2h, Parquet partitionné, agrégats), ``features.build`` (variables T-2h, cibles,
découpage chronologique) et ``data.serving_tables`` (tables de service, table de rejeu).

Sorties (une par dossier, envoyées vers S3 par SageMaker en fin de job) :
``processed/`` (lu par Athena et la Lambda de statistiques), ``ml/``, ``serving/``, ``analytics/``.
Les fichiers Parquet partitionnés sont renommés ``part-<i>.parquet`` : une relance écrase les
mêmes clés S3 au lieu d'ajouter des doublons (le préfixe ``processed/`` est fixe).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from aeropulse import config
from aeropulse.data import pipeline, serving_tables
from aeropulse.features import build


def deterministic_names(dataset_dir: Path) -> int:
    """Renomme les fichiers de chaque partition en ``part-<i>.parquet`` (ordre stable)."""
    renamed = 0
    for partition in sorted({p.parent for p in dataset_dir.rglob("*.parquet")}):
        for i, path in enumerate(sorted(partition.glob("*.parquet"))):
            target = partition / f"part-{i}.parquet"
            if path != target:
                path.rename(target)
            renamed += 1
    return renamed


def run(raw_dir: Path, out_dir: Path, expected_rows: int | None) -> dict[str, object]:
    processed = out_dir / "processed"
    ml_dir, serving_dir, analytics_dir = out_dir / "ml", out_dir / "serving", out_dir / "analytics"
    for d in (processed, ml_dir, serving_dir, analytics_dir):
        if d.exists():
            shutil.rmtree(d)
    report: dict[str, object] = {
        "prepare": pipeline.run(
            raw_dir,
            processed,
            # D-20 : explicite, car ``pipeline.run`` n'applique aucun âge maximal par défaut.
            max_weather_age=pd.Timedelta(config.MAX_WEATHER_AGE),
            expected_rows=expected_rows,
            analytics_dir=analytics_dir,
        )
    }
    report["features"] = build.run(processed, ml_dir)
    sizes = serving_tables.build(processed, raw_dir, serving_dir)
    sizes["replay"] = serving_tables.build_replay(
        ml_dir / "ml_dataset.parquet", serving_dir / "replay.parquet"
    )
    report["serving"] = sizes
    report["partition_files"] = deterministic_names(processed / "flights")
    (ml_dir / "prepare_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-dir", type=Path, default=Path("/opt/ml/processing/input/raw"))
    p.add_argument("--out-dir", type=Path, default=Path("/opt/ml/processing/output"))
    p.add_argument(
        "--expected-rows",
        type=int,
        default=None,
        help="nombre de lignes attendu (0 = pas de contrôle)",
    )
    args = p.parse_args(argv)
    expected = args.expected_rows or None
    print(json.dumps(run(args.raw_dir, args.out_dir, expected), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
