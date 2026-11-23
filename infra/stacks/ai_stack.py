"""Assistant Bedrock : Lambda ``/v1/chat`` et droits d'appel du modèle (CMP-12, version de test).

**Désactivé par défaut** : le modèle Bedrock n'est pas choisi (ADR-0012). Rien de ce module n'est
synthétisé sans ``-c bedrock_model_id=<identifiant>`` (ou ``AEROPULSE_BEDROCK_MODEL_ID``). Le
choix de l'identifiant reste une décision du propriétaire, après vérification de la
disponibilité dans ``us-east-1`` (T8.1).

Garde-fous de coût : 1 requête/s (rafale 2) sur la route, boucle d'outils bornée et jetons de
sortie plafonnés dans l'orchestrateur, quota quotidien du plan d'usage commun à l'API.
La base de connaissances (RAG, D-15) n'est pas créée.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from constructs import Construct

from infra.constants import BUNDLE_POINTER_KEY, PROCESSED_PREFIX, REGION

CHAT_RATE_LIMIT = 1
CHAT_BURST_LIMIT = 2
MAX_TOOL_ROUNDS = 4
MAX_OUTPUT_TOKENS = 800
_GEO_PREFIXES = ("us.", "eu.", "apac.", "global.")


def chat_method_options() -> dict[str, apigw.MethodDeploymentOptions]:
    """Limitation de débit propre à ``POST /v1/chat`` (plus stricte que le reste de l'API)."""
    return {
        "/v1/chat/POST": apigw.MethodDeploymentOptions(
            throttling_rate_limit=CHAT_RATE_LIMIT, throttling_burst_limit=CHAT_BURST_LIMIT
        )
    }


def bedrock_resources(model_id: str, account: str) -> list[str]:
    """ARN autorisés : le modèle demandé seulement (moindre privilège).

    Un identifiant préfixé par une géographie (``us.``…) est un profil d'inférence inter-régions :
    le profil et le modèle de fondation sous-jacent (dans les régions du profil) sont nécessaires.
    À vérifier au premier déploiement réel.
    """
    base = model_id
    for prefix in _GEO_PREFIXES:
        if model_id.startswith(prefix):
            base = model_id[len(prefix) :]
            return [
                f"arn:aws:bedrock:{REGION}:{account}:inference-profile/{model_id}",
                f"arn:aws:bedrock:*::foundation-model/{base}",
            ]
    return [f"arn:aws:bedrock:{REGION}::foundation-model/{base}"]


class AssistantApi(Construct):
    """Lambda de l'assistant branchée sur ``/v1/chat`` de l'API existante."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        v1: apigw.IResource,
        code: lambda_.DockerImageCode,
        data_bucket: s3.IBucket,
        model_id: str,
        environment: dict[str, str],
    ) -> None:
        super().__init__(scope, construct_id)
        stack = cdk.Stack.of(self)
        log_group = logs.LogGroup(
            self,
            "ChatLogs",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        self.function = lambda_.DockerImageFunction(
            self,
            "ChatFunction",
            code=code,
            architecture=lambda_.Architecture.X86_64,
            memory_size=1536,
            timeout=cdk.Duration.seconds(30),  # API Gateway coupe à 29 s
            description="POST /v1/chat (assistant Bedrock, version de test)",
            environment={
                **environment,
                "AEROPULSE_BEDROCK_MODEL_ID": model_id,
                "AEROPULSE_ASSISTANT_MAX_ROUNDS": str(MAX_TOOL_ROUNDS),
                "AEROPULSE_ASSISTANT_MAX_TOKENS": str(MAX_OUTPUT_TOKENS),
                "AEROPULSE_BUNDLE_BUCKET": data_bucket.bucket_name,
                "AEROPULSE_BUNDLE_POINTER": BUNDLE_POINTER_KEY,
                "AEROPULSE_BUNDLE_REFRESH_SECONDS": "300",
                "AEROPULSE_DATA_BUCKET": data_bucket.bucket_name,
                "AEROPULSE_PROCESSED_PREFIX": PROCESSED_PREFIX,
            },
            log_group=log_group,
        )
        data_bucket.grant_read(self.function, "releases/*")
        data_bucket.grant_read(self.function, PROCESSED_PREFIX + "*")
        self.function.add_to_role_policy(
            iam.PolicyStatement(
                sid="InvokeSelectedModelOnly",
                actions=["bedrock:InvokeModel"],
                resources=bedrock_resources(model_id, stack.account),
            )
        )
        v1.add_resource("chat").add_method("POST", apigw.LambdaIntegration(self.function))
        cdk.CfnOutput(stack, "ChatFunctionName", value=self.function.function_name)
