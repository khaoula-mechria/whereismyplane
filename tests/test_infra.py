"""Synthèse CDK sans compte AWS (T6.1–T6.7) : garde-fous de sécurité et de coût vérifiés.

Ne déploie rien : ``aws_cdk.assertions`` lit les modèles CloudFormation produits localement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from infra.app import build_app
from infra.constants import MODEL_PACKAGE_GROUP
from infra.settings import Settings, SettingsError


@pytest.fixture(scope="module")
def stacks(tmp_path_factory: pytest.TempPathFactory) -> dict[str, cdk.Stack]:
    image = tmp_path_factory.mktemp("image")
    (image / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    app = cdk.App(
        context={"budget_email": "alertes@example.com", "runtime_image_dir": str(image)},
        outdir=str(tmp_path_factory.mktemp("cdk.out")),
    )
    return build_app(app)


@pytest.fixture(scope="module")
def templates(stacks: dict[str, cdk.Stack]) -> dict[str, assertions.Template]:
    return {name: assertions.Template.from_stack(stack) for name, stack in stacks.items()}


def _resources(t: assertions.Template, kind: str) -> dict[str, Any]:
    return {k: dict(v) for k, v in t.find_resources(kind).items()}


def test_settings_require_budget_email_and_image(tmp_path: Path) -> None:
    with pytest.raises(SettingsError, match="budget"):
        Settings.from_app(cdk.App(context={"runtime_image_dir": str(tmp_path)}))
    with pytest.raises(SettingsError, match="build_lambda_context"):
        Settings.from_app(
            cdk.App(context={"budget_email": "a@b.co", "runtime_image_dir": str(tmp_path)})
        )


def test_region_is_us_east_1(stacks: dict[str, cdk.Stack]) -> None:
    assert {s.region for s in stacks.values()} == {"us-east-1"}  # ADR-0011


def test_no_sagemaker_endpoint_anywhere(templates: dict[str, assertions.Template]) -> None:
    for t in templates.values():
        for kind in (
            "AWS::SageMaker::Endpoint",
            "AWS::SageMaker::EndpointConfig",
            "AWS::SageMaker::Model",
            "AWS::EC2::NatGateway",
        ):
            assert _resources(t, kind) == {}


def test_buckets_are_private_encrypted_and_tls_only(
    templates: dict[str, assertions.Template],
) -> None:
    for name in ("data", "frontend"):
        t = templates[name]
        for bucket in _resources(t, "AWS::S3::Bucket").values():
            props = bucket["Properties"]
            assert props["PublicAccessBlockConfiguration"] == {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
            assert "BucketEncryption" in props
        policies = json.dumps(_resources(t, "AWS::S3::BucketPolicy"))
        assert "aws:SecureTransport" in policies


def test_athena_scans_are_capped(templates: dict[str, assertions.Template]) -> None:
    templates["data"].has_resource_properties(
        "AWS::Athena::WorkGroup",
        {
            "WorkGroupConfiguration": assertions.Match.object_like(
                {"BytesScannedCutoffPerQuery": 1_000_000_000, "EnforceWorkGroupConfiguration": True}
            )
        },
    )
    templates["data"].resource_count_is("AWS::Athena::NamedQuery", 3)


def test_glue_table_uses_partition_projection(templates: dict[str, assertions.Template]) -> None:
    (table,) = _resources(templates["data"], "AWS::Glue::Table").values()
    params = table["Properties"]["TableInput"]["Parameters"]
    assert params["projection.enabled"] == "true" and params["projection.year.range"] == "2023,2025"


def test_pipeline_and_registry(templates: dict[str, assertions.Template]) -> None:
    t = templates["ml"]
    t.has_resource_properties(
        "AWS::SageMaker::ModelPackageGroup", {"ModelPackageGroupName": MODEL_PACKAGE_GROUP}
    )
    t.has_resource_properties("AWS::SageMaker::Pipeline", {"PipelineName": "aeropulse-training"})
    t.has_resource_properties(
        "AWS::Events::Rule",
        {
            "EventPattern": {
                "source": ["aws.sagemaker"],
                "detail-type": ["SageMaker Model Package State Change"],
                "detail": {
                    "ModelPackageGroupName": [MODEL_PACKAGE_GROUP],
                    "ModelApprovalStatus": ["Approved"],
                },
            }
        },
    )


def test_sagemaker_role_can_only_pass_itself(templates: dict[str, assertions.Template]) -> None:
    policies = json.dumps(_resources(templates["ml"], "AWS::IAM::Policy"))
    assert '"iam:PassedToService": "sagemaker.amazonaws.com"' in policies
    assert '"Action": "*"' not in policies and '"Action": "s3:*"' not in policies


def test_api_requires_key_and_is_throttled(templates: dict[str, assertions.Template]) -> None:
    t = templates["backend"]
    methods = _resources(t, "AWS::ApiGateway::Method")
    assert len(methods) == 4
    assert all(m["Properties"]["ApiKeyRequired"] is True for m in methods.values())
    t.has_resource_properties(
        "AWS::ApiGateway::UsagePlan",
        {
            "Throttle": {"RateLimit": 5, "BurstLimit": 10},
            "Quota": {"Limit": 2000, "Period": "DAY"},
        },
    )
    assert "chat" not in json.dumps(_resources(t, "AWS::ApiGateway::Resource"))  # ADR-0012


def test_lambdas_read_only_their_prefixes(templates: dict[str, assertions.Template]) -> None:
    policies = json.dumps(_resources(templates["backend"], "AWS::IAM::Policy"))
    assert "releases/*" in policies and "processed/flights/*" in policies
    assert "s3:PutObject" not in policies and "s3:DeleteObject" not in policies


def test_every_log_group_has_retention(templates: dict[str, assertions.Template]) -> None:
    for t in templates.values():
        for lg in _resources(t, "AWS::Logs::LogGroup").values():
            assert lg["Properties"]["RetentionInDays"] == 14


def test_budget_alerts_at_50_80_100_percent(templates: dict[str, assertions.Template]) -> None:
    (budget,) = _resources(templates["monitoring"], "AWS::Budgets::Budget").values()
    props = budget["Properties"]
    assert props["Budget"]["BudgetLimit"] == {"Amount": 100, "Unit": "USD"}
    thresholds = sorted(
        (n["Notification"]["NotificationType"], n["Notification"]["Threshold"])
        for n in props["NotificationsWithSubscribers"]
    )
    assert thresholds == [("ACTUAL", 50), ("ACTUAL", 80), ("ACTUAL", 100), ("FORECASTED", 100)]
    templates["monitoring"].resource_count_is("AWS::CloudWatch::Alarm", 5)


def test_frontend_proxies_api_on_same_origin_with_strict_csp(
    templates: dict[str, assertions.Template],
) -> None:
    t = templates["frontend"]
    dist = json.dumps(_resources(t, "AWS::CloudFront::Distribution"))
    assert '"PathPattern": "/v1/*"' in dist
    headers = json.dumps(_resources(t, "AWS::CloudFront::ResponseHeadersPolicy"))
    assert "script-src 'self'" in headers and "unsafe-inline" not in headers


def test_everything_is_tagged(templates: dict[str, assertions.Template]) -> None:
    bucket = next(iter(_resources(templates["data"], "AWS::S3::Bucket").values()))
    tags = {t["Key"]: t["Value"] for t in bucket["Properties"]["Tags"]}
    assert tags["project"] == "aeropulse" and tags["environment"] == "dev"


# --------------------------------------------------------------------------- assistant (test)
def _actions(t: assertions.Template) -> list[str]:
    found: list[str] = []
    for policy in _resources(t, "AWS::IAM::Policy").values():
        for st in policy["Properties"]["PolicyDocument"]["Statement"]:
            acts = st["Action"]
            found.extend(acts if isinstance(acts, list) else [acts])
    return found


def test_assistant_absent_without_model_id(templates: dict[str, assertions.Template]) -> None:
    for t in templates.values():
        assert not [a for a in _actions(t) if a.startswith("bedrock:")]  # ADR-0012
    paths = [
        r["Properties"]["PathPart"]
        for r in _resources(templates["backend"], "AWS::ApiGateway::Resource").values()
    ]
    assert "chat" not in paths


@pytest.fixture(scope="module")
def assistant_templates(tmp_path_factory: pytest.TempPathFactory) -> dict[str, assertions.Template]:
    image = tmp_path_factory.mktemp("image_ai")
    (image / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    app = cdk.App(
        context={
            "budget_email": "alertes@example.com",
            "runtime_image_dir": str(image),
            "bedrock_model_id": "vendor.modele-de-test-v1:0",
        },
        outdir=str(tmp_path_factory.mktemp("cdk.out.ai")),
    )
    built = build_app(app)
    return {name: assertions.Template.from_stack(built[name]) for name in ("backend", "monitoring")}


def test_assistant_route_is_throttled_and_least_privilege(
    assistant_templates: dict[str, assertions.Template],
) -> None:
    t = assistant_templates["backend"]
    paths = [
        r["Properties"]["PathPart"] for r in _resources(t, "AWS::ApiGateway::Resource").values()
    ]
    assert "chat" in paths
    t.has_resource_properties(
        "AWS::ApiGateway::Stage",
        {
            "MethodSettings": assertions.Match.array_with(
                [
                    assertions.Match.object_like(
                        {
                            "HttpMethod": "POST",
                            "ResourcePath": "/~1v1~1chat",
                            "ThrottlingRateLimit": 1,
                        }
                    )
                ]
            )
        },
    )
    t.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Environment": {
                "Variables": assertions.Match.object_like(
                    {"AEROPULSE_BEDROCK_MODEL_ID": "vendor.modele-de-test-v1:0"}
                )
            }
        },
    )
    bedrock = []
    for policy in _resources(t, "AWS::IAM::Policy").values():
        for st in policy["Properties"]["PolicyDocument"]["Statement"]:
            if "bedrock:InvokeModel" in (
                st["Action"] if isinstance(st["Action"], list) else [st["Action"]]
            ):
                bedrock.append(st["Resource"])
    assert bedrock == [
        {
            "Fn::Join": [
                "",
                ["arn:aws:bedrock:us-east-1::foundation-model/vendor.modele-de-test-v1:0"],
            ]
        }
    ] or bedrock == ["arn:aws:bedrock:us-east-1::foundation-model/vendor.modele-de-test-v1:0"]
    assistant_templates["monitoring"].has_resource_properties(
        "AWS::CloudWatch::Alarm", {"AlarmDescription": "Erreurs de la Lambda de l'assistant"}
    )


def test_bedrock_resources_for_cross_region_profiles() -> None:
    from infra.stacks.ai_stack import bedrock_resources

    assert bedrock_resources("us.vendor.modele-v1:0", "123456789012") == [
        "arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.vendor.modele-v1:0",
        "arn:aws:bedrock:*::foundation-model/vendor.modele-v1:0",
    ]


def test_settings_reject_invalid_model_id(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    ctx = {
        "budget_email": "a@b.co",
        "runtime_image_dir": str(tmp_path),
        "bedrock_model_id": "x; rm -rf",
    }
    with pytest.raises(SettingsError, match="Bedrock"):
        Settings.from_app(cdk.App(context=ctx))
