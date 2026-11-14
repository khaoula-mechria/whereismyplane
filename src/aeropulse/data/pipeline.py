"""Pipeline de préparation local : Parquet brut + NOAA -> Parquet partitionné (T2.1–T2.5).

Commande unique (T2.8) : ``uv run python -m aeropulse.data.pipeline [--max-weather-age-minutes N]``
(préparation, validation, Parquet partitionné, agrégats analytiques).
Le seuil d'âge de la météo vient de ``config.MAX_WEATHER_AGE`` (3 h) ; au-delà, la météo est
absente (``NaN``), jamais remplacée.
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
from aeropulse.analytics.engine import Analytics
from aeropulse.data import clean, validate, weather


def run(
    raw_dir: Path,
    out_dir: Path,
    *,
    max_weather_age: pd.Timedelta | None = None,
    expected_rows: int | None = None,
    analytics_dir: Path | None = None,
) -> dict[str, object]:
    raw = pd.read_parquet(raw_dir / "nyc_flight_delays_ml.parquet")
    validate.validate_raw(raw, expected_rows=expected_rows)
    obs = weather.read_noaa(sorted((raw_dir / "noaa").glob("*/*.csv")))
    flights = clean.prepare_flights(raw, obs, max_weather_age=max_weather_age)
    if len(flights) != len(raw):
        raise validate.ValidationError("le nombre de lignes a changé pendant la préparation")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "flights"
    if target.exists():  # relance idempotente : jamais de fichiers cumulés
        shutil.rmtree(target)
    flights.to_parquet(target, partition_cols=["year", "month"], index=False)
    report: dict[str, object] = {
        "rows": len(flights),
        "ml_eligible": int(flights["ml_eligible"].sum()),
        "delayed": int(flights["is_delayed"].fillna(False).sum()),
        "weather_missing": int(flights["weather_missing"].sum()),
        "max_weather_age_minutes": None
        if max_weather_age is None
        else max_weather_age.total_seconds() / 60,
    }
    if analytics_dir is not None:
        engine = Analytics(out_dir / "flights")
        try:
            report["aggregates"] = engine.export_aggregates(analytics_dir)
        finally:
            engine.close()
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--out-dir", type=Path, default=Path("data/processed"))
    p.add_argument("--analytics-dir", type=Path, default=Path("data/analytics"))
    p.add_argument("--no-aggregates", action="store_true", help="ne pas écrire les agrégats")
    p.add_argument(
        "--max-weather-age-minutes",
        type=float,
        default=config.MAX_WEATHER_AGE.total_seconds() / 60,
    )
    p.add_argument("--expected-rows", type=int, default=None)
    args = p.parse_args(argv)
    age = (
        None
        if args.max_weather_age_minutes is None
        else pd.Timedelta(minutes=args.max_weather_age_minutes)
    )
    report = run(
        args.raw_dir,
        args.out_dir,
        max_weather_age=age,
        expected_rows=args.expected_rows,
        analytics_dir=None if args.no_aggregates else args.analytics_dir,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
