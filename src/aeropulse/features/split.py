"""Découpage train/validation/test chronologique (ADR-0004, D-17).

Dates dans ``config`` (sur ``flight_date``, heure locale). Le jeu de test ne sert qu'une fois :
y accéder exige ``final_evaluation=True``.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd

from aeropulse import config

SplitName = Literal["train", "validation", "test"]

_BOUNDS: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {
    "train": (pd.Timestamp(config.TRAIN_START), pd.Timestamp(config.TRAIN_END)),
    "validation": (pd.Timestamp(config.VALIDATION_START), pd.Timestamp(config.VALIDATION_END)),
    "test": (pd.Timestamp(config.TEST_START), pd.Timestamp(config.TEST_END)),
}


def assign_split(flight_date: pd.Series) -> pd.Series:
    """Nom du jeu pour chaque date ; ``ValueError`` si une date n'appartient à aucun jeu."""
    dates = pd.to_datetime(flight_date).dt.normalize()
    out = pd.Series(pd.NA, index=dates.index, dtype="object")
    for name, (start, end) in _BOUNDS.items():
        out[(dates >= start) & (dates <= end)] = name
    if bool(out.isna().any()):
        raise ValueError(f"{int(out.isna().sum())} vols hors de toutes les périodes de découpage")
    return out


def select_split(
    df: pd.DataFrame, name: SplitName, *, final_evaluation: bool = False
) -> pd.DataFrame:
    """Sous-ensemble d'un jeu ; le test n'est accessible que pour l'évaluation finale."""
    if name == "test" and not final_evaluation:
        raise PermissionError("le jeu de test sert une seule fois : final_evaluation=True requis")
    return df[df["split"] == name]
