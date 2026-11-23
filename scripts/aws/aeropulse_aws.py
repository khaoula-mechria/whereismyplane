"""Opérations AWS d'AeroPulse (environnement de test ``dev``, ``us-east-1``).

Utilise les identifiants AWS du poste (profil par défaut ou ``AWS_PROFILE``) ; aucun secret n'est
lu ni écrit dans le dépôt. Les noms des ressources viennent des sorties CloudFormation.

Commandes (``uv run python scripts/aws/aeropulse_aws.py <commande>``) :

- ``whoami`` : compte et identité utilisés ;
- ``outputs`` : sorties des stacks (aucune valeur secrète) ;
- ``upload-raw`` : dépose ``data/raw`` (Parquet + NOAA) dans ``s3://<données>/raw/`` ;
- ``upload-processed`` : dépose ``data/processed/flights`` (noms ``part-<i>.parquet``) ;
- ``publish-local-bundle`` : publie le modèle local vérifié + tables comme bundle actif ;
- ``start-pipeline`` / ``pipeline-status`` : exécution du pipeline SageMaker ;
- ``list-models`` / ``approve <arn>`` : Model Registry (l'approbation déclenche la promotion) ;
- ``rollback`` : remet le pointeur précédent (``releases/previous.json``) ;
- ``api-key`` : affiche la clé d'API de test (dans ce terminal seulement) ;
- ``smoke-test`` : appelle les routes déployées (directement et via CloudFront) ;
- ``check-resources`` : contrôle des ressources facturables (checklist de cost-estimate.md) ;
- ``cleanup-registry --yes`` : supprime les paquets du Model Registry (avant ``cdk destroy``).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aeropulse import config  # noqa: E402
from aeropulse.mlops import bundle, promote  # noqa: E402
from infra.constants import (  # noqa: E402
    BUNDLE_POINTER_KEY,
    MODEL_PACKAGE_GROUP,
    PREVIOUS_POINTER_KEY,
    PROCESSED_PREFIX,
    RAW_PREFIX,
    REGION,
    STACKS,
)

PIPELINE_NAME = "aeropulse-training"


def _boto(service: str) -> Any:
    import boto3

    return boto3.client(service, region_name=REGION)


def stack_outputs(stack: str) -> dict[str, str]:
    cf = _boto("cloudformation")
    try:
        desc = cf.describe_stacks(StackName=stack)["Stacks"][0]
    except Exception as exc:
        raise SystemExit(f"stack {stack} introuvable : déployer d'abord (infra/README.md)") from exc
    return {o["OutputKey"]: o["OutputValue"] for o in desc.get("Outputs", [])}


def data_bucket() -> str:
    return stack_outputs(STACKS["data"])["DataBucketName"]


def partition_keys(dataset_dir: Path, prefix: str) -> list[tuple[Path, str]]:
    """Fichiers d'un Parquet partitionné -> clés S3 ``<prefix><partition>/part-<i>.parquet``."""
    pairs: list[tuple[Path, str]] = []
    for partition in sorted({p.parent for p in dataset_dir.rglob("*.parquet")}):
        rel = partition.relative_to(dataset_dir).as_posix()
        for i, path in enumerate(sorted(partition.glob("*.parquet"))):
            pairs.append((path, f"{prefix}{rel}/part-{i}.parquet"))
    return pairs


def raw_keys(raw_dir: Path) -> list[tuple[Path, str]]:
    files = [raw_dir / "nyc_flight_delays_ml.parquet", *sorted((raw_dir / "noaa").glob("*/*.csv"))]
    missing = [str(f) for f in files[:1] if not f.is_file()]
    if missing or len(files) == 1:
        raise SystemExit(f"données brutes absentes sous {raw_dir} (dataset-card.md)")
    return [(f, RAW_PREFIX + f.relative_to(raw_dir).as_posix()) for f in files]


def _upload(pairs: list[tuple[Path, str]], bucket: str) -> None:
    s3 = _boto("s3")
    total = 0
    for path, key in pairs:
        s3.upload_file(str(path), bucket, key)
        total += path.stat().st_size
    print(f"{len(pairs)} fichiers, {total / 1e6:.1f} Mo -> s3://{bucket}/")


def cmd_whoami(_: argparse.Namespace) -> int:
    ident = _boto("sts").get_caller_identity()
    print(json.dumps({"account": ident["Account"], "arn": ident["Arn"], "region": REGION}))
    return 0


def cmd_outputs(_: argparse.Namespace) -> int:
    out = {name: stack_outputs(stack) for name, stack in STACKS.items()}
    print(json.dumps(out, indent=2))
    return 0


def cmd_upload_raw(args: argparse.Namespace) -> int:
    _upload(raw_keys(args.raw_dir), data_bucket())
    return 0


def cmd_upload_processed(args: argparse.Namespace) -> int:
    pairs = partition_keys(args.processed_dir, PROCESSED_PREFIX)
    if not pairs:
        raise SystemExit(f"aucun Parquet sous {args.processed_dir} : lancer data.pipeline")
    _upload(pairs, data_bucket())
    return 0


def publish_bundle(
    s3: Any, bucket: str, release_dir: Path, serving_dir: Path, source: str
) -> dict[str, Any]:
    """Vérifie, archive et publie un bundle, puis déplace le pointeur (ancien -> previous)."""
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / "staged"
        info = bundle.stage_bundle(release_dir, serving_dir, staged)
        archive = Path(tmp) / "bundle.tar.gz"
        digest = bundle.make_archive(staged, archive)
        bundle.extract_bundle(archive, Path(tmp) / "check")  # même contrôle que la Lambda
        key = f"releases/{info['model_version']}/bundle.tar.gz"
        s3.upload_file(str(archive), bucket, key)
    pointer = {
        "model_version": info["model_version"],
        "bundle_key": key,
        "sha256": digest,
        "source": source,
        "promoted_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    promote.write_pointer(s3, bucket, pointer, BUNDLE_POINTER_KEY)
    return pointer


def cmd_publish_local_bundle(args: argparse.Namespace) -> int:
    pointer = publish_bundle(
        _boto("s3"), data_bucket(), args.release_dir, args.serving_dir, "bootstrap-local"
    )
    print(json.dumps(pointer, indent=2))
    print("La Lambda bascule au plus tard après 5 min (conteneurs déjà démarrés).")
    return 0


def cmd_start_pipeline(_: argparse.Namespace) -> int:
    sm = _boto("sagemaker")
    res = sm.start_pipeline_execution(
        PipelineName=PIPELINE_NAME,
        PipelineExecutionDisplayName=f"manual-{datetime.now(UTC):%Y%m%d-%H%M%S}",
    )
    print(res["PipelineExecutionArn"])
    print("Suivi : pipeline-status ; coût indicatif : quelques minutes de ml.m5.large par étape.")
    return 0


def cmd_pipeline_status(args: argparse.Namespace) -> int:
    sm = _boto("sagemaker")
    arn = args.execution_arn
    if not arn:
        runs = sm.list_pipeline_executions(PipelineName=PIPELINE_NAME, MaxResults=1)
        summaries = runs.get("PipelineExecutionSummaries", [])
        if not summaries:
            print("aucune exécution")
            return 0
        arn = summaries[0]["PipelineExecutionArn"]
    desc = sm.describe_pipeline_execution(PipelineExecutionArn=arn)
    print(f"{arn}\nstatut : {desc['PipelineExecutionStatus']}")
    if desc.get("FailureReason"):
        print(f"échec : {desc['FailureReason']}")
    steps = sm.list_pipeline_execution_steps(PipelineExecutionArn=arn)["PipelineExecutionSteps"]
    for step in reversed(steps):
        reason = f" — {step['FailureReason']}" if step.get("FailureReason") else ""
        print(f"  {step['StepName']:<14} {step['StepStatus']}{reason}")
    return 0


def cmd_list_models(_: argparse.Namespace) -> int:
    sm = _boto("sagemaker")
    res = sm.list_model_packages(
        ModelPackageGroupName=MODEL_PACKAGE_GROUP, SortBy="CreationTime", SortOrder="Descending"
    )
    for pkg in res.get("ModelPackageSummaryList", []):
        created = pkg["CreationTime"].strftime("%Y-%m-%d %H:%M")
        print(f"{pkg['ModelPackageArn']}  {pkg['ModelApprovalStatus']}  {created}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    if not args.yes:
        raise SystemExit("ajouter --yes : l'approbation promeut le modèle vers l'API de test")
    _boto("sagemaker").update_model_package(
        ModelPackageArn=args.arn,
        ModelApprovalStatus="Approved",
        ApprovalDescription=args.note or "approuvé manuellement (environnement de test)",
    )
    print("approuvé : la Lambda de promotion publie le bundle (journaux : AeroPulse-ML).")
    return 0


def cmd_rollback(_: argparse.Namespace) -> int:
    s3, bucket = _boto("s3"), data_bucket()
    previous = s3.get_object(Bucket=bucket, Key=PREVIOUS_POINTER_KEY)["Body"].read()
    current = s3.get_object(Bucket=bucket, Key=BUNDLE_POINTER_KEY)["Body"].read()
    s3.put_object(Bucket=bucket, Key=BUNDLE_POINTER_KEY, Body=previous)
    s3.put_object(Bucket=bucket, Key=PREVIOUS_POINTER_KEY, Body=current)
    print("pointeur rétabli :", json.loads(previous)["model_version"])
    return 0


def api_key_value() -> str:
    key_id = stack_outputs(STACKS["backend"])["ApiKeyId"]
    return str(_boto("apigateway").get_api_key(apiKey=key_id, includeValue=True)["value"])


def cmd_api_key(_: argparse.Namespace) -> int:
    print(api_key_value())
    return 0


def http(method: str, url: str, key: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("x-api-key", key)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.status, json.loads(res.read() or b"null")
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, raw.decode(errors="replace")[:200]


def sample_requests(serving_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Un vol réel de la période de test : requête de rejeu et saisie manuelle équivalente."""
    import pandas as pd

    row = pd.read_parquet(serving_dir / "replay.parquet").iloc[0]
    flight_id = str(row["flight_id"])
    day, _, origin, hhmm = flight_id.split("_")
    carrier = str(row["carrier"])
    local = datetime.strptime(f"{day} {hhmm}", "%Y-%m-%d %H%M").replace(
        tzinfo=ZoneInfo(config.LOCAL_TIMEZONE)
    )
    manual = {
        "airline": carrier,
        "origin": origin,
        "destination": str(row["destination"]),
        "scheduled_departure": local.isoformat(),
    }
    return {"flight_id": flight_id}, manual


def cmd_smoke_test(args: argparse.Namespace) -> int:
    api = stack_outputs(STACKS["backend"])["ApiUrl"].rstrip("/")
    site = stack_outputs(STACKS["frontend"])["SiteUrl"].rstrip("/")
    key = api_key_value()
    replay, manual = sample_requests(args.serving_dir)
    checks: list[tuple[str, Callable[[], tuple[int, Any]], int]] = [
        ("GET /v1/health", lambda: http("GET", f"{api}/v1/health", key), 200),
        ("GET /v1/meta", lambda: http("GET", f"{api}/v1/meta", key), 200),
        ("GET /v1/stats/airport", lambda: http("GET", f"{api}/v1/stats/airport", key), 200),
        ("POST /v1/predict (rejeu)", lambda: http("POST", f"{api}/v1/predict", key, replay), 200),
        ("POST /v1/predict (manuel)", lambda: http("POST", f"{api}/v1/predict", key, manual), 200),
        ("POST /v1/predict invalide", lambda: http("POST", f"{api}/v1/predict", key, {}), 400),
        ("GET /v1/health sans clé", lambda: http("GET", f"{api}/v1/health", ""), 403),
        ("CloudFront /v1/health", lambda: http("GET", f"{site}/v1/health", key), 200),
    ]
    failures = 0
    for name, call, expected in checks:
        start = time.perf_counter()
        status, body = call()
        ms = (time.perf_counter() - start) * 1000
        ok = status == expected
        failures += not ok
        detail = ""
        if isinstance(body, dict) and "delay_probability" in body:
            detail = f" p={body['delay_probability']} modèle={body['model_versions']}"
        elif isinstance(body, dict) and "model_versions" in body:
            detail = f" modèle={body['model_versions']}"
        print(f"{'OK ' if ok else 'KO '} {name:<28} {status} ({ms:.0f} ms){detail}")
    print(f"console de test : {site}")
    return 1 if failures else 0


def cmd_check_resources(args: argparse.Namespace) -> int:
    sm, ec2 = _boto("sagemaker"), _boto("ec2")
    report: dict[str, Any] = {
        "sagemaker_endpoints": [e["EndpointName"] for e in sm.list_endpoints()["Endpoints"]],
        "processing_jobs_running": [
            j["ProcessingJobName"]
            for j in sm.list_processing_jobs(StatusEquals="InProgress")["ProcessingJobSummaries"]
        ],
        "training_jobs_running": [
            j["TrainingJobName"]
            for j in sm.list_training_jobs(StatusEquals="InProgress")["TrainingJobSummaries"]
        ],
        "nat_gateways": [
            n["NatGatewayId"]
            for n in ec2.describe_nat_gateways(
                Filters=[{"Name": "state", "Values": ["available", "pending"]}]
            )["NatGateways"]
        ],
    }
    try:
        bucket, s3, size = data_bucket(), _boto("s3"), 0
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
            size += sum(o["Size"] for o in page.get("Contents", []))
        report["data_bucket_mb"] = round(size / 1e6, 1)
    except SystemExit:
        report["data_bucket_mb"] = None
    if args.cost:  # Cost Explorer : 0,01 USD par requête
        ce = _boto("ce")
        today = datetime.now(UTC).date()
        res = ce.get_cost_and_usage(
            TimePeriod={"Start": today.replace(day=1).isoformat(), "End": today.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        total = res["ResultsByTime"][0]["Total"]["UnblendedCost"] if res["ResultsByTime"] else {}
        report["month_to_date_cost"] = total
    print(json.dumps(report, indent=2, default=str))
    billable = report["sagemaker_endpoints"] or report["nat_gateways"]
    return 1 if billable else 0


def cmd_cleanup_registry(args: argparse.Namespace) -> int:
    if not args.yes:
        raise SystemExit("ajouter --yes : supprime tous les paquets du groupe de modèles")
    sm = _boto("sagemaker")
    paginator = sm.get_paginator("list_model_packages")
    n = 0
    for page in paginator.paginate(ModelPackageGroupName=MODEL_PACKAGE_GROUP):
        for pkg in page.get("ModelPackageSummaryList", []):
            sm.delete_model_package(ModelPackageName=pkg["ModelPackageArn"])
            n += 1
    print(f"{n} paquet(s) supprimé(s) du groupe {MODEL_PACKAGE_GROUP}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("whoami").set_defaults(func=cmd_whoami)
    sub.add_parser("outputs").set_defaults(func=cmd_outputs)
    s = sub.add_parser("upload-raw")
    s.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    s.set_defaults(func=cmd_upload_raw)
    s = sub.add_parser("upload-processed")
    s.add_argument("--processed-dir", type=Path, default=ROOT / "data" / "processed" / "flights")
    s.set_defaults(func=cmd_upload_processed)
    s = sub.add_parser("publish-local-bundle")
    s.add_argument("--release-dir", type=Path, default=ROOT / "data" / "ml" / "release")
    s.add_argument("--serving-dir", type=Path, default=ROOT / "data" / "serving")
    s.set_defaults(func=cmd_publish_local_bundle)
    sub.add_parser("start-pipeline").set_defaults(func=cmd_start_pipeline)
    s = sub.add_parser("pipeline-status")
    s.add_argument("--execution-arn")
    s.set_defaults(func=cmd_pipeline_status)
    sub.add_parser("list-models").set_defaults(func=cmd_list_models)
    s = sub.add_parser("approve")
    s.add_argument("arn")
    s.add_argument("--note")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(func=cmd_approve)
    sub.add_parser("rollback").set_defaults(func=cmd_rollback)
    sub.add_parser("api-key").set_defaults(func=cmd_api_key)
    s = sub.add_parser("smoke-test")
    s.add_argument("--serving-dir", type=Path, default=ROOT / "data" / "serving")
    s.set_defaults(func=cmd_smoke_test)
    s = sub.add_parser("check-resources")
    s.add_argument("--cost", action="store_true", help="coût du mois (Cost Explorer, 0,01 USD)")
    s.set_defaults(func=cmd_check_resources)
    s = sub.add_parser("cleanup-registry")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(func=cmd_cleanup_registry)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
