"""Garde-fou budgétaire quotidien : signale tout endpoint SageMaker actif (règle du projet).

Le projet n'en crée aucun (inférence dans la Lambda, ADR-0018) ; un endpoint présent est donc un
oubli ou une création manuelle. La fonction **notifie** (SNS) et ne supprime rien : la
suppression reste une décision humaine.
"""

from __future__ import annotations

import json
import os
from typing import Any


def active_endpoints(sm: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    paginator = sm.get_paginator("list_endpoints")
    for page in paginator.paginate():
        for ep in page.get("Endpoints", []):
            found.append({"name": str(ep["EndpointName"]), "status": str(ep["EndpointStatus"])})
    return found


def check(sm: Any, sns: Any, topic_arn: str) -> dict[str, Any]:
    endpoints = active_endpoints(sm)
    if endpoints:
        names = ", ".join(f"{e['name']} ({e['status']})" for e in endpoints)
        sns.publish(
            TopicArn=topic_arn,
            Subject="AeroPulse : endpoint SageMaker actif",
            Message=(
                f"{len(endpoints)} endpoint(s) SageMaker présent(s) en us-east-1 : {names}. "
                "Un endpoint est facturé en continu ; le supprimer s'il n'est pas utilisé."
            ),
        )
    return {"endpoints": endpoints, "alerted": bool(endpoints)}


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    import boto3  # fourni par le runtime Lambda

    result = check(boto3.client("sagemaker"), boto3.client("sns"), os.environ["ALERT_TOPIC_ARN"])
    print(json.dumps(result))
    return result
