"""Construction de ``ml_dataset`` (T3.8) : variables T-2h + cibles + découpage.

Une seule implémentation, partagée entre entraînement et service (CMP-05). Le contrat de variables
(``config.FEATURE_COLUMNS``) est vérifié contre les colonnes interdites avant toute écriture.
Commande : ``uv run python -m aeropulse.features.build``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from aeropulse import config
from aeropulse.features import history, split, targets, temporal
from aeropulse.features import weather as weather_features

ID_COLUMNS = ("flight_date", "carrier", "flight_number", "origin", "scheduled_departure_utc")


def build_ml_dataset(flights: pd.DataFrame) -> pd.DataFrame:
    """Retourne les lignes éligibles au ML avec ``FEATURE_COLUMNS``, cibles et ``split``."""
    config.assert_no_forbidden_columns(config.FEATURE_COLUMNS)
    df = temporal.add_temporal_features(flights)
    df = weather_features.add_weather_features(df)
    df = history.add_history_features(df)  # calculé sur tous les vols : passé strict seulement
    df = targets.add_targets(df)
    df = df[df["ml_eligible"].astype(bool)].copy()
    df["split"] = split.assign_split(df["flight_date"])
    columns = [
        *dict.fromkeys([*ID_COLUMNS, *config.FEATURE_COLUMNS]),
        config.TARGET_CLASSIFICATION,
        config.TARGET_REGRESSION,
        "split",
    ]
    return df[columns].reset_index(drop=True)


def run(processed_dir: Path, out_dir: Path) -> dict[str, object]:
    flights = pd.read_parquet(processed_dir / "flights")
    ml = build_ml_dataset(flights)
    out_dir.mkdir(parents=True, exist_ok=True)
    ml.to_parquet(out_dir / "ml_dataset.parquet", index=False)
    sizes = ml["split"].value_counts().to_dict()
    report: dict[str, object] = {
        "rows": len(ml),
        "split": {k: int(sizes.get(k, 0)) for k in ("train", "validation", "test")},
        "delay_rate": {
            name: float(ml.loc[ml["split"] == name, config.TARGET_CLASSIFICATION].mean())
            for name in (
                "train",
                "validation",
            )  # le test n'est pas regardé avant l'évaluation finale
        },
        "missing_rate": {c: round(float(ml[c].isna().mean()), 4) for c in config.NUMERIC_FEATURES},
    }
    (out_dir / "ml_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    p.add_argument("--out-dir", type=Path, default=Path("data/ml"))
    args = p.parse_args(argv)
    print(json.dumps(run(args.processed_dir, args.out_dir), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
