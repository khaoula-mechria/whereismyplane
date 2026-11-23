"""Outils statistiques : compagnie, aéroport, itinéraire, vue d'ensemble (FR-19, FR-20).

Ils délèguent au moteur analytique (requêtes prédéfinies, listes blanches, limite plafonnée,
seuil de 30 vols) ; ils n'exécutent aucun SQL eux-mêmes.
"""

from __future__ import annotations

from typing import Any

from aeropulse.analytics import queries
from aeropulse.analytics.engine import Analytics
from aeropulse.tools.schemas import AIRPORT, MONTH, YEAR, ToolError, ToolSpec

ROW_LIMIT = 10

AIRLINE = ToolSpec(
    name="get_airline_delay_statistics",
    description="Taux de retard (> 15 min) et taille d'échantillon d'une compagnie, "
    "optionnellement à un aéroport et sur une année ou un mois.",
    properties={
        "airline": {"type": "string", "description": "Code compagnie IATA, par exemple AA"},
        "airport": AIRPORT,
        "year": YEAR,
        "month": MONTH,
    },
    required=("airline",),
)
AIRPORT_SPEC = ToolSpec(
    name="get_airport_delay_statistics",
    description="Taux de retard (> 15 min) et taille d'échantillon d'un aéroport de départ.",
    properties={"airport": AIRPORT, "year": YEAR, "month": MONTH},
    required=("airport",),
)
ROUTE = ToolSpec(
    name="get_route_delay_statistics",
    description="Taux de retard (> 15 min) d'un itinéraire origine → destination.",
    properties={
        "origin": AIRPORT,
        "destination": {"type": "string", "description": "Code IATA de destination"},
        "year": YEAR,
        "month": MONTH,
    },
    required=("origin", "destination"),
)
OVERVIEW = ToolSpec(
    name="get_flight_statistics",
    description="Vue d'ensemble : vols, taux de retard global et par aéroport.",
    properties={"year": YEAR, "month": MONTH},
)


def _period(args: dict[str, Any]) -> dict[str, Any]:
    return {k: args[k] for k in ("year", "month") if k in args}


def _query(analytics: Analytics, dimension: str, filters: dict[str, object]) -> dict[str, Any]:
    try:
        return analytics.statistics(dimension, filters, ROW_LIMIT)
    except queries.InvalidParameterError as exc:
        raise ToolError(str(exc)) from exc


def _package(result: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    rows = result["rows"]
    return {
        "source": result["source"],
        "filters": args,
        "rows": rows,
        "n_flights": sum(int(r["n_flights"]) for r in rows),
        "note": "historique, pas une prévision ; moins de 30 vols : données insuffisantes",
    }


def airline_statistics(analytics: Analytics, args: dict[str, Any]) -> dict[str, Any]:
    filters: dict[str, object] = {"carrier": args["airline"], **_period(args)}
    if "airport" in args:
        filters["origin"] = args["airport"]
    return _package(_query(analytics, "carrier", filters), args)


def airport_statistics(analytics: Analytics, args: dict[str, Any]) -> dict[str, Any]:
    filters: dict[str, object] = {"origin": args["airport"], **_period(args)}
    return _package(_query(analytics, "airport", filters), args)


def route_statistics(analytics: Analytics, args: dict[str, Any]) -> dict[str, Any]:
    filters: dict[str, object] = {
        "origin": args["origin"],
        "destination": args["destination"],
        **_period(args),
    }
    return _package(_query(analytics, "route", filters), args)


def flight_statistics(analytics: Analytics, args: dict[str, Any]) -> dict[str, Any]:
    out = _package(_query(analytics, "airport", dict(_period(args))), args)
    scored = [r for r in out["rows"] if r["sufficient"]]
    n_scored = sum(int(r["n_scored"]) for r in scored)
    delayed = sum(float(r["delay_rate"]) * int(r["n_scored"]) for r in scored)
    out["overall_delay_rate"] = round(delayed / n_scored, 4) if n_scored else None
    return out
