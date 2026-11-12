"""Manifeste des fichiers sources à acquérir (T1.1, ADR-0016).

Deux sources d'origine :
- BTS On-Time Reporting Carrier : une archive mensuelle nationale (filtrée ensuite par origine).
- NOAA Global Hourly : un CSV par station et par année.

Le motif exact des noms de fichiers BTS est incertain (avec ou sans parenthèses dans
`(1987_present)`, voir docs/data-acquisition-study.md §3) : on génère les deux candidats et
on résout par requête HEAD.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal
from urllib.parse import quote

from aeropulse import config

BTS_BASE = "https://www.transtats.bts.gov/PREZIP/"
NOAA_BASE = "https://noaa-global-hourly-pds.s3.amazonaws.com/"

_BTS_PREFIX = "On_Time_Reporting_Carrier_On_Time_Performance_"


@dataclass(frozen=True)
class SourceFile:
    source: Literal["bts", "noaa"]
    name: str
    url: str
    relpath: str  # chemin relatif au dossier raw


def study_months() -> Iterator[tuple[int, int]]:
    """Mois (année, mois) de la période d'étude, bornes incluses."""
    y, m = config.STUDY_START.year, config.STUDY_START.month
    while (y, m) <= (config.STUDY_END.year, config.STUDY_END.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def bts_candidates(year: int, month: int) -> list[SourceFile]:
    """Noms candidats pour un mois BTS : sans puis avec parenthèses."""
    names = [
        f"{_BTS_PREFIX}1987_present_{year}_{month}.zip",
        f"{_BTS_PREFIX}(1987_present)_{year}_{month}.zip",
    ]
    return [
        SourceFile(
            source="bts",
            name=name,
            url=BTS_BASE + quote(name, safe=""),
            relpath=f"bts/{year}_{month:02d}.zip",
        )
        for name in names
    ]


def noaa_files() -> list[SourceFile]:
    """Un CSV par station et par année couverte par la période d'étude."""
    years = range(config.STUDY_START.year, config.STUDY_END.year + 1)
    return [
        SourceFile(
            source="noaa",
            name=f"{year}/{station}.csv",
            url=f"{NOAA_BASE}{year}/{station}.csv",
            relpath=f"noaa/{year}/{airport}_{station}.csv",
        )
        for year in years
        for airport, station in config.NOAA_STATIONS.items()
    ]
