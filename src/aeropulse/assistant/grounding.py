"""Garde-fou « aucun chiffre inventé » (NFR-06, FR-21, AC-14).

Tout nombre écrit dans la réponse finale doit être l'arrondi d'un nombre présent dans les
résultats des outils, dans la question de l'utilisateur, ou dans les constantes publiques du
projet (seuil de 15 min, horizon de 2 h, seuil de 30 vols). Les pourcentages sont acceptés quand
ils arrondissent un taux renvoyé par un outil (0,2413 → « 24,1 % »). Sinon la réponse est retirée.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

from aeropulse import config

# Nombre écrit à la française ou à l'anglaise : 1 056 897 · 24,1 · 0.241 · 2025-03-14 (découpé).
_NUMBER = re.compile(r"(?<![\w.,])\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")
_PUBLIC = (
    config.DELAY_THRESHOLD_MINUTES,
    config.PREDICTION_HORIZON.total_seconds() / 3600,
    config.MIN_SAMPLE_SIZE,
)


def numbers_in_text(text: str) -> list[tuple[float, int]]:
    """Nombres écrits dans un texte, avec leur nombre de décimales affichées."""
    found: list[tuple[float, int]] = []
    for match in _NUMBER.finditer(text):
        raw = re.sub(r"[   ]", "", match.group()).replace(",", ".")
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        found.append((float(raw), decimals))
    return found


def _walk(value: Any) -> Iterable[float]:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int | float):
        if math.isfinite(float(value)):
            yield float(value)
    elif isinstance(value, str):
        for number, _ in numbers_in_text(value):
            yield number
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _walk(item)


def allowed_numbers(tool_results: list[Any], user_message: str) -> list[float]:
    base = [*(_walk(tool_results)), *(n for n, _ in numbers_in_text(user_message)), *_PUBLIC]
    # un taux de 0 à 1 peut être cité en pourcentage
    return base + [v * 100 for v in base if 0 <= v <= 1]


def ungrounded_numbers(answer: str, allowed: list[float]) -> list[float]:
    """Nombres de la réponse qui ne sont l'arrondi d'aucun nombre autorisé."""
    bad: list[float] = []
    for value, decimals in numbers_in_text(answer):
        tolerance = 0.5 * 10 ** (-decimals) + 1e-9
        if not any(abs(value - a) <= tolerance for a in allowed):
            bad.append(value)
    return bad
