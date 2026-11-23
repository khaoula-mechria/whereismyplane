"""Définition SageMaker Pipelines (CMP-08, T5.3–T5.5) : JSON construit sans SDK SageMaker.

Étapes : ``Prepare`` (Processing) → ``Train`` (Training) → ``Evaluate`` (Processing, D-22 sur la
validation) → ``QualityGate`` (Condition) → ``Register`` (Model Registry, **approbation
manuelle**) ou ``QualityFailed`` (Fail). Aucun endpoint n'est créé : l'approbation déclenche la
promotion du bundle vers la Lambda (``aeropulse.mlops.promote``, ADR-0018).

Les valeurs (bucket, rôle, image) peuvent être des jetons CDK : la définition est sérialisée par
``Stack.to_json_string`` dans ``infra/stacks/ml_stack.py``.
"""

from __future__ import annotations

from typing import Any

PIPELINE_NAME = "aeropulse-training"
DEFAULT_INSTANCE_TYPE = "ml.m5.large"
DEFAULT_EXPECTED_ROWS = "1056897"  # profil vérifié du fichier brut (dataset-card.md)
MAX_RUNTIME_SECONDS = 3600
VOLUME_GB = 30
PROC = "/opt/ml/processing"


def _get(path: str) -> dict[str, str]:
    return {"Get": path}


def _join(*values: Any) -> dict[str, Any]:
    return {"Std:Join": {"On": "/", "Values": list(values)}}


def _run_prefix(bucket: str, name: str) -> dict[str, Any]:
    """``s3://<bucket>/runs/<id d'exécution>/<name>`` : artefacts traçables par exécution."""
    return _join(f"s3://{bucket}/runs", _get("Execution.PipelineExecutionId"), name)


def _s3_input(name: str, uri: Any, local: str) -> dict[str, Any]:
    return {
        "InputName": name,
        "AppManaged": False,
        "S3Input": {
            "S3Uri": uri,
            "LocalPath": local,
            "S3DataType": "S3Prefix",
            "S3InputMode": "File",
            "S3DataDistributionType": "FullyReplicated",
            "S3CompressionType": "None",
        },
    }


def _s3_output(name: str, uri: Any) -> dict[str, Any]:
    return {
        "OutputName": name,
        "AppManaged": False,
        "S3Output": {
            "S3Uri": uri,
            "LocalPath": f"{PROC}/output/{name}",
            "S3UploadMode": "EndOfJob",
        },
    }


def _cluster(instance_param: str) -> dict[str, Any]:
    return {
        "ClusterConfig": {
            "InstanceType": _get(f"Parameters.{instance_param}"),
            "InstanceCount": 1,
            "VolumeSizeInGB": VOLUME_GB,
        }
    }


def _output_uri(step: str, output: str) -> dict[str, str]:
    return _get(f"Steps.{step}.ProcessingOutputConfig.Outputs['{output}'].S3Output.S3Uri")


def build_definition(
    *, bucket: str, role_arn: str, image_uri: str, model_package_group: str
) -> dict[str, Any]:
    stopping = {"MaxRuntimeInSeconds": MAX_RUNTIME_SECONDS}
    env = {"PYTHONUNBUFFERED": "1"}

    prepare = {
        "Name": "Prepare",
        "Type": "Processing",
        "Arguments": {
            "ProcessingResources": _cluster("ProcessingInstanceType"),
            "AppSpecification": {
                "ImageUri": image_uri,
                "ContainerEntrypoint": ["python3", "-m", "aeropulse.mlops.prepare_job"],
                "ContainerArguments": [
                    "--raw-dir",
                    f"{PROC}/input/raw",
                    "--out-dir",
                    f"{PROC}/output",
                    "--expected-rows",
                    _get("Parameters.ExpectedRows"),
                ],
            },
            "RoleArn": role_arn,
            "ProcessingInputs": [_s3_input("raw", f"s3://{bucket}/raw", f"{PROC}/input/raw")],
            "ProcessingOutputConfig": {
                "Outputs": [
                    # Préfixe fixe : table Athena et Lambda de statistiques.
                    _s3_output("processed", f"s3://{bucket}/processed"),
                    _s3_output("ml", _run_prefix(bucket, "ml")),
                    _s3_output("serving", _run_prefix(bucket, "serving")),
                    _s3_output("analytics", _run_prefix(bucket, "analytics")),
                ]
            },
            "StoppingCondition": stopping,
            "Environment": env,
        },
    }

    train = {
        "Name": "Train",
        "Type": "Training",
        "Arguments": {
            # Pas de ContainerEntrypoint : l'image reçoit l'argument « train » (entrypoint.sh).
            "AlgorithmSpecification": {"TrainingImage": image_uri, "TrainingInputMode": "File"},
            "RoleArn": role_arn,
            "InputDataConfig": [
                {
                    "ChannelName": channel,
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": _output_uri("Prepare", channel),
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    },
                }
                for channel in ("ml", "serving")
            ],
            "OutputDataConfig": {"S3OutputPath": _run_prefix(bucket, "model")},
            "ResourceConfig": {
                "InstanceType": _get("Parameters.TrainingInstanceType"),
                "InstanceCount": 1,
                "VolumeSizeInGB": VOLUME_GB,
            },
            "StoppingCondition": stopping,
            "Environment": env,
        },
    }

    model_data = _get("Steps.Train.ModelArtifacts.S3ModelArtifacts")
    evaluate = {
        "Name": "Evaluate",
        "Type": "Processing",
        "Arguments": {
            "ProcessingResources": _cluster("ProcessingInstanceType"),
            "AppSpecification": {
                "ImageUri": image_uri,
                "ContainerEntrypoint": ["python3", "-m", "aeropulse.mlops.evaluate_job"],
                "ContainerArguments": [
                    "--model",
                    f"{PROC}/input/model/model.tar.gz",
                    "--ml-dataset",
                    f"{PROC}/input/ml/ml_dataset.parquet",
                    "--out",
                    f"{PROC}/output/evaluation/evaluation.json",
                ],
            },
            "RoleArn": role_arn,
            "ProcessingInputs": [
                _s3_input("model", model_data, f"{PROC}/input/model"),
                _s3_input("ml", _output_uri("Prepare", "ml"), f"{PROC}/input/ml"),
            ],
            "ProcessingOutputConfig": {
                "Outputs": [_s3_output("evaluation", _run_prefix(bucket, "evaluation"))]
            },
            "StoppingCondition": stopping,
            "Environment": env,
        },
        "PropertyFiles": [
            {
                "PropertyFileName": "EvaluationReport",
                "OutputName": "evaluation",
                "FilePath": "evaluation.json",
            }
        ],
    }

    register = {
        "Name": "Register",
        "Type": "RegisterModel",
        "Arguments": {
            "ModelPackageGroupName": model_package_group,
            "ModelPackageDescription": (
                "Classifieur XGBoost retard > 15 min à T-2h ; bundle de service (modèle + tables)"
            ),
            "ModelApprovalStatus": "PendingManualApproval",
            "InferenceSpecification": {
                "Containers": [{"Image": image_uri, "ModelDataUrl": model_data}],
                "SupportedContentTypes": ["application/json"],
                "SupportedResponseMIMETypes": ["application/json"],
            },
            "ModelMetrics": {
                "ModelQuality": {
                    "Statistics": {
                        "ContentType": "application/json",
                        "S3Uri": _join(_output_uri("Evaluate", "evaluation"), "evaluation.json"),
                    }
                }
            },
        },
    }

    failed = {
        "Name": "QualityFailed",
        "Type": "Fail",
        "Arguments": {
            "ErrorMessage": (
                "Contrôle de qualité D-22 en échec sur la validation : modèle non enregistré "
                "(détail dans evaluation.json)."
            )
        },
    }

    gate = {
        "Name": "QualityGate",
        "Type": "Condition",
        "Arguments": {
            "Conditions": [
                {
                    "Type": "Equals",
                    "LeftValue": {
                        "Std:JsonGet": {
                            "PropertyFile": _get("Steps.Evaluate.PropertyFiles.EvaluationReport"),
                            "Path": "quality.passed_flag",
                        }
                    },
                    "RightValue": 1,
                }
            ],
            "IfSteps": [register],
            "ElseSteps": [failed],
        },
    }

    return {
        "Version": "2020-12-01",
        "Metadata": {},
        "Parameters": [
            {
                "Name": "ProcessingInstanceType",
                "Type": "String",
                "DefaultValue": DEFAULT_INSTANCE_TYPE,
            },
            {
                "Name": "TrainingInstanceType",
                "Type": "String",
                "DefaultValue": DEFAULT_INSTANCE_TYPE,
            },
            {"Name": "ExpectedRows", "Type": "String", "DefaultValue": DEFAULT_EXPECTED_ROWS},
        ],
        # Pas de PipelineExperimentConfig : pas de SageMaker Experiments (droits IAM en moins).
        "Steps": [prepare, train, evaluate, gate],
    }
