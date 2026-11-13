"""Requêtes SQL paramétrées prédéfinies (T2.7, FR-04, AC-13, AC-15).

Aucune chaîne SQL ne vient de l'appelant : les dimensions et les filtres sont choisis dans des
listes blanches, les valeurs sont liées par paramètres (``?``), la limite de lignes est plafonnée.
Lecture seule. Une statistique calculée sur moins de ``config.MIN_SAMPLE_SIZE`` vols n'est pas
renvoyée (« données insuffisantes »).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from aeropulse import config

DEFAULT_LIMIT: Final = 20
MAX_LIMIT: Final = 100

# Dimensions autorisées -> colonnes SQL (constantes du module, jamais fournies par l'appelant).
DIMENSIONS: Final = {
    "carrier": ("carrier",),
    "airport": ("origin",),
    "route": ("origin", "destination"),
}
# Filtres autorisés -> fragment SQL fixe.
FILTERS: Final = {
    "carrier": "carrier = ?",
    "origin": "origin = ?",
    "destination": "destination = ?",
    "year": "year = ?",
    "month": "month = ?",
}
_CODE = re.compile(r"^[A-Z0-9]{2,3}$")


class InvalidParameterError(ValueError):
    """Paramètre hors liste blanche, mal formé ou hors limites."""


@dataclass(frozen=True)
class Allowed:
    """Valeurs autorisées pour les filtres textuels (issues des données, jamais de l'appelant)."""

    carriers: frozenset[str]
    airports: frozenset[str]
    destinations: frozenset[str]


@dataclass(frozen=True)
class Query:
    sql: str
    params: tuple[object, ...]
    limit: int
    keys: tuple[str, ...]


def _validate_code(name: str, value: object, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or not _CODE.fullmatch(value.upper()):
        raise InvalidParameterError(f"{name} : format invalide")
    code = value.upper()
    if code not in allowed:
        raise InvalidParameterError(f"{name} : valeur inconnue")
    return code


def _validate_int(name: str, value: object, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise InvalidParameterError(f"{name} : entier entre {low} et {high} attendu")
    return value


def validate_filters(filters: dict[str, object], allowed: Allowed) -> dict[str, object]:
    """Vérifie les filtres ; toute clé hors liste blanche est refusée."""
    unknown = sorted(set(filters) - set(FILTERS))
    if unknown:
        raise InvalidParameterError(f"filtres non autorisés : {unknown}")
    clean: dict[str, object] = {}
    for name, value in filters.items():
        if value is None:
            continue
        if name == "carrier":
            clean[name] = _validate_code(name, value, allowed.carriers)
        elif name == "origin":
            clean[name] = _validate_code(name, value, allowed.airports)
        elif name == "destination":
            clean[name] = _validate_code(name, value, allowed.destinations)
        elif name == "year":
            clean[name] = _validate_int(name, value, config.STUDY_START.year, config.STUDY_END.year)
        else:
            clean[name] = _validate_int(name, value, 1, 12)
    return clean


def validate_limit(limit: object) -> int:
    return _validate_int("limit", DEFAULT_LIMIT if limit is None else limit, 1, MAX_LIMIT)


def build_statistics_query(
    dimension: str, filters: dict[str, object], limit: object, allowed: Allowed
) -> Query:
    """Statistiques de retard groupées par ``dimension`` (compagnie, aéroport ou itinéraire)."""
    if dimension not in DIMENSIONS:
        raise InvalidParameterError(f"dimension : une valeur parmi {sorted(DIMENSIONS)}")
    clean = validate_filters(filters, allowed)
    n = validate_limit(limit)
    keys = DIMENSIONS[dimension]
    where = " AND ".join(FILTERS[name] for name in clean) or "TRUE"
    cols = ", ".join(keys)
    # Fragments fixes issus de listes blanches ; les valeurs sont liées par `?`.
    sql = f"""
        SELECT {cols},
               count(*) AS n_flights,
               count(*) FILTER (WHERE ml_eligible) AS n_scored,
               count(*) FILTER (WHERE cancelled) AS n_cancelled,
               count(*) FILTER (WHERE diverted) AS n_diverted,
               count(*) FILTER (WHERE ml_eligible AND is_delayed) AS n_delayed,
               avg(departure_delay_minutes) FILTER (WHERE ml_eligible) AS mean_departure_delay_min,
               min(flight_date) AS period_start,
               max(flight_date) AS period_end
        FROM flights
        WHERE {where}
        GROUP BY {cols}
        ORDER BY n_flights DESC, {cols}
    """
    return Query(sql, tuple(clean.values()), n, keys)
