from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aeropulse.data import pipeline, validate

NOAA_HEADER = '"STATION","DATE","REPORT_TYPE","TMP","DEW","WND","VIS","CIG","SLP"'


def _write_inputs(raw_dir: Path, n: int = 40) -> None:
    flights = pd.DataFrame(
        {
            "flight_date": ["2024-01-01"] * n,
            "carrier": ["AA"] * n,
            "flight_number": [str(i) for i in range(n)],
            "origin": ["JFK"] * n,
            "destination": ["LAX"] * n,
            "scheduled_departure_hhmm": ["0700"] * n,
            "month": [1] * n,
            "scheduled_elapsed_minutes": ["300"] * n,
            "distance_miles": ["2475"] * n,
            "departure_delay_minutes": [str(i) for i in range(n)],
            "arrival_delay_minutes": ["0"] * n,
            "cancelled": [False] * n,
            "diverted": [False] * n,
            "scheduled_departure_utc": pd.to_datetime(["2024-01-01T12:00:00Z"] * n),
        }
    )
    raw_dir.mkdir(parents=True)
    flights.to_parquet(raw_dir / "nyc_flight_delays_ml.parquet", index=False)
    noaa = raw_dir / "noaa" / "2024"
    noaa.mkdir(parents=True)
    fields = ["74486094789", "2024-01-01T09:51:00", "FM-15", "+0056,5", "-0028,5"]
    fields += ["260,5,N,0041,5", "016093,5,N,5", "01524,5,M,N", "10163,5"]
    row = ",".join(f'"{f}"' for f in fields)
    (noaa / "JFK_74486094789.csv").write_text(f"{NOAA_HEADER}\n{row}\n", encoding="utf-8")


def test_end_to_end(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    _write_inputs(raw_dir)
    out, agg = tmp_path / "processed", tmp_path / "analytics"
    report = pipeline.run(raw_dir, out, expected_rows=40, analytics_dir=agg)
    assert report["rows"] == 40 and report["ml_eligible"] == 40
    assert report["delayed"] == 24  # retards 16..39 min
    assert report["weather_missing"] == 0
    assert report["aggregates"] == {"carrier": 1, "airport": 1, "route": 1}
    assert json.loads((out / "report.json").read_text(encoding="utf-8"))["rows"] == 40
    reread = pd.read_parquet(out / "flights")
    assert len(reread) == 40 and (reread["weather_age_minutes"] == 9).all()


def test_blocks_when_row_count_differs(tmp_path: Path) -> None:
    _write_inputs(tmp_path / "raw")
    with pytest.raises(validate.ValidationError):
        pipeline.run(tmp_path / "raw", tmp_path / "out", expected_rows=41)
    assert not (tmp_path / "out").exists()


def test_rerun_is_idempotent(tmp_path: Path) -> None:
    _write_inputs(tmp_path / "raw")
    out = tmp_path / "processed"
    pipeline.run(tmp_path / "raw", out, expected_rows=40)
    pipeline.run(tmp_path / "raw", out, expected_rows=40)
    assert len(pd.read_parquet(out / "flights")) == 40
