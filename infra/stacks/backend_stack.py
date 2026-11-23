"""BackendStack : Lambdas (image d'exécution) et API Gateway REST (CMP-10, CMP-11, CMP-15).

Routes (toutes avec clé d'API, D-05) :

| Méthode | Route | Lambda |
|---|---|---|
| GET | ``/v1/health`` | prédiction (version du modèle chargé) |
| POST | ``/v1/predict`` | prédiction (saisie manuelle ou rejeu, D-02) |
| GET | ``/v1/meta`` | statistiques (listes autorisées, période) |
| GET | ``/v1/stats/{dimension}`` | statistiques (carrier, airport, route) |

``POST /v1/chat`` (assistant, version de test) n'existe que si ``-c bedrock_model_id=...`` est
fourni : le modèle Bedrock n'est pas choisi (ADR-0012), voir ``infra/stacks/ai_stack.py``.
Limitation de débit (protection du budget) : 5 requêtes/s, rafale 10, 2 000 requêtes/jour par
clé. Inférence **dans la Lambda** (aucun endpoint SageMaker, ADR-0018).
"""

from __future__ import annotations

from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from constructs import Construct

from infra.constants import BUNDLE_POINTER_KEY, PROCESSED_PREFIX
from infra.settings import Settings
from infra.stacks.ai_stack import AssistantApi, chat_method_options

STAGE = "live"
RATE_LIMIT = 5
BURST_LIMIT = 10
DAILY_QUOTA = 2000


class BackendStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        settings: Settings,
        data_bucket: s3.IBucket,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        def image(cmd: str) -> lambda_.DockerImageCode:
            return lambda_.DockerImageCode.from_image_asset(
                str(settings.runtime_image_dir),
                cmd=[cmd],
                platform=ecr_assets.Platform.LINUX_AMD64,
            )

        def log_group(name: str) -> logs.LogGroup:
            return logs.LogGroup(
                self,
                name,
                retention=logs.RetentionDays.TWO_WEEKS,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            )

        common_env = {"HOME": "/tmp", "AEROPULSE_WORK_DIR": "/tmp/aeropulse"}
        self.predict_fn = lambda_.DockerImageFunction(
            self,
            "PredictFunction",
            code=image("aeropulse.api.predict_handler.handler"),
            architecture=lambda_.Architecture.X86_64,
            memory_size=1536,
            timeout=cdk.Duration.seconds(60),
            description="POST /v1/predict et GET /v1/health (modèle en processus)",
            environment={
                **common_env,
                "AEROPULSE_BUNDLE_BUCKET": data_bucket.bucket_name,
                "AEROPULSE_BUNDLE_POINTER": BUNDLE_POINTER_KEY,
                "AEROPULSE_BUNDLE_REFRESH_SECONDS": "300",
            },
            log_group=log_group("PredictLogs"),
        )
        data_bucket.grant_read(self.predict_fn, "releases/*")

        self.stats_fn = lambda_.DockerImageFunction(
            self,
            "StatsFunction",
            code=image("aeropulse.api.stats_handler.handler"),
            architecture=lambda_.Architecture.X86_64,
            memory_size=1024,
            timeout=cdk.Duration.seconds(60),
            description="GET /v1/meta et /v1/stats/{dimension} (DuckDB lecture seule)",
            environment={
                **common_env,
                "AEROPULSE_DATA_BUCKET": data_bucket.bucket_name,
                "AEROPULSE_PROCESSED_PREFIX": PROCESSED_PREFIX,
            },
            log_group=log_group("StatsLogs"),
        )
        data_bucket.grant_read(self.stats_fn, PROCESSED_PREFIX + "*")

        self.api = apigw.RestApi(
            self,
            "Api",
            rest_api_name="aeropulse-api",
            description="AeroPulse API v1 (environnement de test)",
            endpoint_types=[apigw.EndpointType.REGIONAL],
            cloud_watch_role=False,  # pas de réglage de compte API Gateway (journaux d'exécution)
            deploy_options=apigw.StageOptions(
                stage_name=STAGE,
                throttling_rate_limit=RATE_LIMIT,
                throttling_burst_limit=BURST_LIMIT,
                metrics_enabled=True,
                method_options=chat_method_options() if settings.bedrock_model_id else None,
            ),
            default_method_options=apigw.MethodOptions(api_key_required=True),
        )
        predict = apigw.LambdaIntegration(self.predict_fn)
        stats = apigw.LambdaIntegration(self.stats_fn)
        v1 = self.api.root.add_resource("v1")
        v1.add_resource("health").add_method("GET", predict)
        v1.add_resource("predict").add_method("POST", predict)
        v1.add_resource("meta").add_method("GET", stats)
        v1.add_resource("stats").add_resource("{dimension}").add_method("GET", stats)

        self.chat_fn: lambda_.IFunction | None = None
        if settings.bedrock_model_id:
            assistant = AssistantApi(
                self,
                "Assistant",
                v1=v1,
                code=image("aeropulse.api.assistant_handler.handler"),
                data_bucket=data_bucket,
                model_id=settings.bedrock_model_id,
                environment=common_env,
            )
            self.chat_fn = assistant.function

        key = self.api.add_api_key("TestApiKey", api_key_name="aeropulse-test")
        plan = self.api.add_usage_plan(
            "UsagePlan",
            name="aeropulse-test",
            description="Protection du budget : débit et quota par clé",
            throttle=apigw.ThrottleSettings(rate_limit=RATE_LIMIT, burst_limit=BURST_LIMIT),
            quota=apigw.QuotaSettings(limit=DAILY_QUOTA, period=apigw.Period.DAY),
        )
        plan.add_api_key(key)
        plan.add_api_stage(stage=self.api.deployment_stage)

        cdk.CfnOutput(self, "ApiUrl", value=self.api.url)
        cdk.CfnOutput(self, "ApiKeyId", value=key.key_id)
        cdk.CfnOutput(self, "PredictFunctionName", value=self.predict_fn.function_name)
        cdk.CfnOutput(self, "StatsFunctionName", value=self.stats_fn.function_name)
