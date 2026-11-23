"""Définition SageMaker Pipelines : structure, références entre étapes, aucun endpoint (T5.3)."""

from __future__ import annotations

import importlib.util
import json
import re
from typing import Any

from pipelines.sagemaker.pipeline import build_definition

DEF = build_definition(
    bucket="bucket-x",
    role_arn="arn:aws:iam::123456789012:role/sm",
    image_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/repo:tag",
    model_package_group="aeropulse-delay-classifier",
)


def _all_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step in steps:
        out.append(step)
        if step["Type"] == "Condition":
            out += _all_steps(step["Arguments"]["IfSteps"] + step["Arguments"]["ElseSteps"])
    return out


def test_steps_order_and_types() -> None:
    steps = {s["Name"]: s["Type"] for s in _all_steps(DEF["Steps"])}
    assert steps == {
        "Prepare": "Processing",
        "Train": "Training",
        "Evaluate": "Processing",
        "QualityGate": "Condition",
        "Register": "RegisterModel",
        "QualityFailed": "Fail",
    }


def test_no_endpoint_or_model_deployment_step() -> None:
    text = json.dumps(DEF)
    assert "Endpoint" not in text and 'CreateModel"' not in text


def test_registration_requires_manual_approval_and_quality_gate() -> None:
    gate = next(s for s in DEF["Steps"] if s["Name"] == "QualityGate")
    cond = gate["Arguments"]["Conditions"][0]
    assert cond["LeftValue"]["Std:JsonGet"]["Path"] == "quality.passed_flag"
    assert cond["RightValue"] == 1
    register = gate["Arguments"]["IfSteps"][0]
    assert register["Arguments"]["ModelApprovalStatus"] == "PendingManualApproval"


def test_step_references_point_to_declared_outputs_and_parameters() -> None:
    text = json.dumps(DEF)
    params = {p["Name"] for p in DEF["Parameters"]}
    for ref in re.findall(r'"Get": "Parameters\.(\w+)"', text):
        assert ref in params
    outputs = {
        (s["Name"], o["OutputName"])
        for s in _all_steps(DEF["Steps"])
        if s["Type"] == "Processing"
        for o in s["Arguments"]["ProcessingOutputConfig"]["Outputs"]
    }
    for step, name in re.findall(r"Steps\.(\w+)\.ProcessingOutputConfig\.Outputs\['(\w+)'\]", text):
        assert (step, name) in outputs
    evaluate = next(s for s in DEF["Steps"] if s["Name"] == "Evaluate")
    (prop,) = evaluate["PropertyFiles"]
    assert prop["OutputName"] in {o for s, o in outputs if s == "Evaluate"}


def test_container_entrypoints_are_importable_modules() -> None:
    for step in _all_steps(DEF["Steps"]):
        entry = step["Arguments"].get("AppSpecification", {}).get("ContainerEntrypoint")
        if entry:
            assert entry[:2] == ["python3", "-m"]
            assert importlib.util.find_spec(entry[2]) is not None
    assert importlib.util.find_spec("aeropulse.mlops.train_job") is not None


def test_processed_output_is_the_fixed_athena_prefix() -> None:
    prepare = DEF["Steps"][0]
    outputs = {
        o["OutputName"]: o["S3Output"]["S3Uri"]
        for o in prepare["Arguments"]["ProcessingOutputConfig"]["Outputs"]
    }
    assert outputs["processed"] == "s3://bucket-x/processed"
    assert "Execution.PipelineExecutionId" in json.dumps(outputs["ml"])  # traçabilité par exécution
