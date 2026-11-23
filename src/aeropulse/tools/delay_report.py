"""Outil generate_delay_report (CMP-13, FR-22, AC-17).

Met en forme des résultats **déjà calculés** dans la conversation en cours : le modèle de
langage ne fournit qu'un titre, jamais de chiffres. Le rapport ne peut donc contenir aucun chiffre
absent de ses données d'entrée.
"""

from __future__ import annotations

import json
from typing import Any

from aeropulse.tools.schemas import ToolError, ToolSpec

REPORT = ToolSpec(
    name="generate_delay_report",
    description="Rapport Markdown à partir des résultats d'outils déjà obtenus dans cette "
    "conversation (n'ajoute aucun chiffre).",
    properties={"title": {"type": "string", "description": "Titre court du rapport"}},
    required=("title",),
)


def _line(name: str, result: dict[str, Any]) -> list[str]:
    lines = [f"### {name}", f"- source : {result.get('source', 'inconnue')}"]
    for row in result.get("rows", []):
        key = ", ".join(str(row[k]) for k in ("carrier", "origin", "destination") if k in row)
        rate = row.get("delay_rate")
        shown = "données insuffisantes" if rate is None else f"{rate}"
        lines.append(
            f"- {key} : taux de retard {shown} sur {row.get('n_scored')} vols, "
            f"période {row.get('period', {}).get('start')} → {row.get('period', {}).get('end')}"
        )
    if "delay_probability" in result:
        lines.append(f"- probabilité de retard : {result['delay_probability']}")
    if "overall_delay_rate" in result:
        lines.append(f"- taux de retard global : {result['overall_delay_rate']}")
    return lines


def generate_delay_report(args: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [h for h in history if h.get("tool") != REPORT.name and "result" in h]
    if not usable:
        raise ToolError("aucun résultat d'outil à mettre en forme : appeler d'abord un outil")
    lines = [f"## {args['title']}"]
    for item in usable:
        lines.extend(_line(str(item["tool"]), item["result"]))
    return {
        "source": "résultats d'outils de cette conversation",
        "report_markdown": "\n".join(lines),
        "inputs": json.loads(json.dumps([h["tool"] for h in usable])),
    }
