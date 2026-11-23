"""MLStack : pipeline SageMaker, Model Registry, promotion vers l'API (CMP-08, CMP-09).

- Image d'exécution unique (``DockerImageAsset``) pour les jobs Processing et Training ;
- rôle SageMaker au moindre privilège (préfixes S3 précis, image en lecture, journaux) ;
- groupe de modèles ``aeropulse-delay-classifier`` (approbation **manuelle**) ;
- pipeline ``aeropulse-training`` (``pipelines/sagemaker/pipeline.py``) ;
- règle EventBridge « paquet approuvé » → Lambda de promotion (copie du bundle vérifié et
  écriture du pointeur ``releases/current.json``).

**Aucun endpoint SageMaker** n'est créé (ADR-0018) : rien n'est facturé hors exécution du
pipeline (quelques minutes d'instance ml.m5.large par exécution).
"""

from __future__ import annotations

from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct

from infra.constants import BUNDLE_POINTER_KEY, MODEL_PACKAGE_GROUP
from infra.settings import Settings
from pipelines.sagemaker.pipeline import PIPELINE_NAME, build_definition

ZIP_EXCLUDES = ["**/__pycache__", "**/*.pyc"]


def src_code(settings: Settings) -> lambda_.Code:
    """Code source du paquet pour les petites Lambdas sans dépendance (archive zip)."""
    return lambda_.Code.from_asset(str(settings.src_dir), exclude=ZIP_EXCLUDES)


class MLStack(cdk.Stack):
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

        image = ecr_assets.DockerImageAsset(
            self,
            "RuntimeImage",
            directory=str(settings.runtime_image_dir),
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        role = iam.Role(
            self,
            "SageMakerRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            description="AeroPulse : pipeline et jobs SageMaker (moindre privilège)",
        )
        data_bucket.grant_read(role, "raw/*")
        data_bucket.grant_read_write(role, "processed/*")
        data_bucket.grant_read_write(role, "runs/*")
        image.repository.grant_pull(role)

        arn = f"arn:aws:sagemaker:{self.region}:{self.account}"
        role.add_to_policy(
            iam.PolicyStatement(
                sid="PipelineJobs",
                actions=[
                    "sagemaker:CreateProcessingJob",
                    "sagemaker:DescribeProcessingJob",
                    "sagemaker:StopProcessingJob",
                    "sagemaker:CreateTrainingJob",
                    "sagemaker:DescribeTrainingJob",
                    "sagemaker:StopTrainingJob",
                    "sagemaker:AddTags",
                    "sagemaker:ListTags",
                ],
                resources=[f"{arn}:processing-job/*", f"{arn}:training-job/*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                sid="ModelRegistry",
                actions=[
                    "sagemaker:CreateModelPackage",
                    "sagemaker:DescribeModelPackage",
                    "sagemaker:DescribeModelPackageGroup",
                    "sagemaker:AddTags",
                    "sagemaker:ListTags",
                ],
                resources=[
                    f"{arn}:model-package-group/{MODEL_PACKAGE_GROUP}",
                    f"{arn}:model-package/{MODEL_PACKAGE_GROUP}/*",
                ],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                sid="PassOwnRole",
                actions=["iam:PassRole"],
                resources=[role.role_arn],
                conditions={"StringEquals": {"iam:PassedToService": "sagemaker.amazonaws.com"}},
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                sid="JobLogs",
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/sagemaker/*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                sid="JobMetrics",
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={"StringLike": {"cloudwatch:namespace": "/aws/sagemaker/*"}},
            )
        )

        group = sagemaker.CfnModelPackageGroup(
            self,
            "ModelPackageGroup",
            model_package_group_name=MODEL_PACKAGE_GROUP,
            model_package_group_description=(
                "Classifieur retard > 15 min à T-2h (JFK/EWR/LGA) ; approbation manuelle"
            ),
        )

        definition = build_definition(
            bucket=data_bucket.bucket_name,
            role_arn=role.role_arn,
            image_uri=image.image_uri,
            model_package_group=MODEL_PACKAGE_GROUP,
        )
        pipeline = sagemaker.CfnPipeline(
            self,
            "TrainingPipeline",
            pipeline_name=PIPELINE_NAME,
            pipeline_display_name=PIPELINE_NAME,
            pipeline_description="Prepare -> Train -> Evaluate (D-22) -> Register (manuel)",
            role_arn=role.role_arn,
            pipeline_definition={"PipelineDefinitionBody": self.to_json_string(definition)},
        )
        pipeline.node.add_dependency(group)
        pipeline.node.add_dependency(role)

        promote = lambda_.Function(
            self,
            "PromoteFunction",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="aeropulse.mlops.promote.handler",
            code=src_code(settings),
            memory_size=512,
            timeout=cdk.Duration.minutes(2),
            description="Promotion d'un modèle approuvé : bundle vérifié + pointeur current.json",
            environment={
                "AEROPULSE_MODEL_PACKAGE_GROUP": MODEL_PACKAGE_GROUP,
                "AEROPULSE_BUNDLE_BUCKET": data_bucket.bucket_name,
                "AEROPULSE_BUNDLE_POINTER": BUNDLE_POINTER_KEY,
            },
            log_group=logs.LogGroup(
                self,
                "PromoteLogs",
                retention=logs.RetentionDays.TWO_WEEKS,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            ),
        )
        data_bucket.grant_read(promote, "runs/*")
        data_bucket.grant_read_write(promote, "releases/*")
        promote.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sagemaker:DescribeModelPackage"],
                resources=[f"{arn}:model-package/{MODEL_PACKAGE_GROUP}/*"],
            )
        )
        events.Rule(
            self,
            "ModelApprovedRule",
            description="Paquet AeroPulse approuvé dans le Model Registry -> promotion",
            event_pattern=events.EventPattern(
                source=["aws.sagemaker"],
                detail_type=["SageMaker Model Package State Change"],
                detail={
                    "ModelPackageGroupName": [MODEL_PACKAGE_GROUP],
                    "ModelApprovalStatus": ["Approved"],
                },
            ),
            targets=[targets.LambdaFunction(promote, retry_attempts=2)],
        )

        self.image = image
        cdk.CfnOutput(self, "PipelineName", value=PIPELINE_NAME)
        cdk.CfnOutput(self, "ModelPackageGroupName", value=MODEL_PACKAGE_GROUP)
        cdk.CfnOutput(self, "SageMakerRoleArn", value=role.role_arn)
        cdk.CfnOutput(self, "PromoteFunctionName", value=promote.function_name)
