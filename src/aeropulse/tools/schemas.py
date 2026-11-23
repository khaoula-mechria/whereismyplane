"""Schémas d'entrée et de sortie des outils, listes blanches (FR-20, AC-15).

Chaque outil déclare un schéma JSON strict (aucune propriété supplémentaire). Les valeurs
textuelles sont ensuite validées par les listes blanches du moteur analytique ou du service de
prédiction : aucune chaîne fournie par le modèle de langage n'atteint une requête SQL.
Chaque sortie porte ``source``, ``period`` et ``n_flights`` quand ces notions s'appliquent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

MAX_STRING_LENGTH = 40


class ToolError(ValueError):
    """Appel d'outil refusé : outil inconnu, paramètre absent, hors liste ou mal typé."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    properties: dict[str, dict[str, Any]]
    required: tuple[str, ...] = field(default=())

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": self.properties,
            "required": list(self.required),
            "additionalProperties": False,
        }


def check_args(spec: ToolSpec, args: object) -> dict[str, Any]:
    """Vérifie la forme des arguments ; les valeurs sont validées ensuite par le domaine."""
    if not isinstance(args, Mapping):
        raise ToolError(f"{spec.name} : les arguments doivent être un objet")
    unknown = sorted(set(args) - set(spec.properties))
    if unknown:
        raise ToolError(f"{spec.name} : paramètres non autorisés {unknown}")
    missing = [name for name in spec.required if args.get(name) in (None, "")]
    if missing:
        raise ToolError(f"{spec.name} : paramètres manquants {missing}")
    clean: dict[str, Any] = {}
    for name, value in args.items():
        if value is None:
            continue
        kind = spec.properties[name].get("type")
        if kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ToolError(f"{spec.name} : {name} doit être un entier")
        elif kind == "string" and (
            not isinstance(value, str) or not 0 < len(value) <= MAX_STRING_LENGTH
        ):
            raise ToolError(f"{spec.name} : {name} doit être un texte court")
        clean[name] = value
    return clean


YEAR = {"type": "integer", "description": "Année (2023 à 2025), optionnelle"}
MONTH = {"type": "integer", "description": "Mois (1 à 12), optionnel"}
AIRPORT = {"type": "string", "description": "Aéroport de départ : JFK, EWR ou LGA"}
