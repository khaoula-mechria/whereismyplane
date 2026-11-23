"""Paramètres communs de l'application CDK : région, nommage, étiquettes, contexte.

Région imposée ``us-east-1`` (ADR-0011). Aucune valeur sensible n'est versionnée : l'adresse de
notification du budget vient du contexte ``-c budget_email=...`` ou de la variable
d'environnement ``AEROPULSE_BUDGET_EMAIL`` (jamais de ``cdk.context.json`` committé).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import aws_cdk as cdk

from infra.constants import ENVIRONMENT, PROJECT, REGION

ROOT = Path(__file__).resolve().parent.parent
TAGS = {"project": PROJECT, "environment": ENVIRONMENT, "managed-by": "cdk"}
DEFAULT_BUDGET_USD = 100  # D-12b
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MODEL_ID = re.compile(r"^[a-z0-9][a-z0-9.\-:]{2,127}$")


class SettingsError(ValueError):
    """Paramètre de déploiement manquant ou invalide."""


@dataclass(frozen=True)
class Settings:
    budget_email: str
    budget_usd: int
    runtime_image_dir: Path
    src_dir: Path
    site_dir: Path
    account: str | None
    bedrock_model_id: str | None = None  # assistant désactivé si absent (ADR-0012)

    @staticmethod
    def from_app(app: cdk.App) -> Settings:
        email = app.node.try_get_context("budget_email") or os.environ.get(
            "AEROPULSE_BUDGET_EMAIL", ""
        )
        if not _EMAIL.fullmatch(str(email)):
            raise SettingsError(
                "adresse de notification du budget requise : "
                "-c budget_email=<adresse> ou AEROPULSE_BUDGET_EMAIL"
            )
        image_dir = Path(str(app.node.try_get_context("runtime_image_dir") or "build/runtime"))
        if not image_dir.is_absolute():
            image_dir = ROOT / image_dir
        if not (image_dir / "Dockerfile").is_file():
            raise SettingsError(
                f"contexte d'image absent ({image_dir}) : lancer "
                "`uv run python scripts/build_lambda_context.py` avant `cdk synth/deploy`"
            )
        budget = int(app.node.try_get_context("budget_usd") or DEFAULT_BUDGET_USD)
        model_id = str(
            app.node.try_get_context("bedrock_model_id")
            or os.environ.get("AEROPULSE_BEDROCK_MODEL_ID", "")
        ).strip()
        if model_id and not _MODEL_ID.fullmatch(model_id):
            raise SettingsError(f"identifiant de modèle Bedrock invalide : {model_id!r}")
        return Settings(
            budget_email=str(email),
            budget_usd=budget,
            runtime_image_dir=image_dir,
            src_dir=ROOT / "src",
            site_dir=ROOT / "frontend" / "test-console",
            account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
            bedrock_model_id=model_id or None,
        )

    @property
    def env(self) -> cdk.Environment:
        return cdk.Environment(account=self.account, region=REGION)
