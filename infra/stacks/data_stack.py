"""DataStack : bucket S3, catalogue Glue, workgroup Athena (CMP-01, CMP-03, CMP-04).

Un seul bucket privé, chiffré, TLS obligatoire, préfixes :

- ``raw/`` : données brutes déposées depuis le poste (Parquet Mostly Right + NOAA) ;
- ``processed/flights/year=/month=/`` : sortie de l'étape « Prepare » (table Athena ``flights``) ;
- ``runs/<exécution>/`` : artefacts de chaque exécution du pipeline (expirés après 90 jours) ;
- ``releases/`` : bundles promus et pointeur ``current.json`` lu par la Lambda ;
- ``athena-results/`` : résultats Athena (expirés après 7 jours).

La table Glue utilise la **projection de partitions** (pas de crawler, pas de MSCK REPAIR). Les
requêtes nommées Athena sont générées par ``analytics.queries`` (même SQL que DuckDB, T6.3).
Destruction complète à ``cdk destroy`` (environnement de test, AC-12) : les données brutes
restent sur le poste local.
"""

from __future__ import annotations

from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_athena as athena
from aws_cdk import aws_glue as glue
from aws_cdk import aws_s3 as s3
from constructs import Construct

from aeropulse import config
from aeropulse.analytics import queries
from infra.constants import PROCESSED_PREFIX, PROJECT

DATABASE = PROJECT
TABLE = "flights"
WORKGROUP = PROJECT
ATHENA_SCAN_LIMIT_BYTES = 1_000_000_000  # 1 Go par requête (≈ 0,005 USD), garde-fou budgétaire

# Schéma lu sur le Parquet préparé réel (pyarrow, 2026-11-21) ; year/month = partitions.
FLIGHT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("flight_date", "date"),
    ("carrier", "string"),
    ("flight_number", "string"),
    ("origin", "string"),
    ("destination", "string"),
    ("scheduled_departure_hhmm", "string"),
    ("departure_hour", "bigint"),
    ("day_of_week", "bigint"),
    ("scheduled_elapsed_minutes", "double"),
    ("distance_miles", "double"),
    ("departure_delay_minutes", "double"),
    ("arrival_delay_minutes", "double"),
    ("departure_delayed_15", "boolean"),
    ("arrival_delayed_15", "boolean"),
    ("cancelled", "boolean"),
    ("diverted", "boolean"),
    ("scheduled_departure_utc", "timestamp"),
    ("origin_name", "string"),
    ("origin_latitude", "double"),
    ("origin_longitude", "double"),
    ("destination_name", "string"),
    ("destination_latitude", "double"),
    ("destination_longitude", "double"),
    ("feature_cutoff_utc", "timestamp"),
    ("temperature_c", "double"),
    ("dewpoint_c", "double"),
    ("wind_speed_mps", "double"),
    ("visibility_m", "double"),
    ("ceiling_m", "double"),
    ("sea_level_pressure_hpa", "double"),
    ("weather_observed_utc", "timestamp"),
    ("weather_age_minutes", "double"),
    ("weather_missing", "boolean"),
    ("ml_eligible", "boolean"),
    ("is_delayed", "boolean"),
)


def named_query_sql(dimension: str) -> str:
    """SQL prédéfini de ``analytics.queries`` (sans filtre), exécutable tel quel par Athena."""
    no_filter = queries.Allowed(frozenset(), frozenset(), frozenset())
    q = queries.build_statistics_query(dimension, {}, queries.MAX_LIMIT, no_filter)
    return q.sql.strip() + f"\nLIMIT {q.limit}"


class DataStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = s3.Bucket(
            self,
            "DataBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="athena-results",
                    prefix="athena-results/",
                    expiration=cdk.Duration.days(7),
                ),
                s3.LifecycleRule(
                    id="pipeline-runs", prefix="runs/", expiration=cdk.Duration.days(90)
                ),
                s3.LifecycleRule(
                    id="abort-multipart",
                    abort_incomplete_multipart_upload_after=cdk.Duration.days(1),
                ),
            ],
        )
        bucket_name = self.bucket.bucket_name

        database = glue.CfnDatabase(
            self,
            "Database",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=DATABASE, description="AeroPulse : vols JFK/EWR/LGA préparés (2023-2025)"
            ),
        )
        location = f"s3://{bucket_name}/{PROCESSED_PREFIX}"
        table = glue.CfnTable(
            self,
            "FlightsTable",
            catalog_id=self.account,
            database_name=DATABASE,
            table_input=glue.CfnTable.TableInputProperty(
                name=TABLE,
                description="Sortie de l'étape Prepare (data.pipeline) ; lecture seule",
                table_type="EXTERNAL_TABLE",
                parameters={
                    "classification": "parquet",
                    "EXTERNAL": "TRUE",
                    "projection.enabled": "true",
                    "projection.year.type": "integer",
                    "projection.year.range": f"{config.STUDY_START.year},{config.STUDY_END.year}",
                    "projection.month.type": "integer",
                    "projection.month.range": "1,12",
                    "storage.location.template": location + "year=${year}/month=${month}/",
                },
                partition_keys=[
                    glue.CfnTable.ColumnProperty(name="year", type="int"),
                    glue.CfnTable.ColumnProperty(name="month", type="int"),
                ],
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    location=location,
                    input_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library=(
                            "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
                        )
                    ),
                    columns=[
                        glue.CfnTable.ColumnProperty(name=n, type=t) for n, t in FLIGHT_COLUMNS
                    ],
                ),
            ),
        )
        table.node.add_dependency(database)

        workgroup = athena.CfnWorkGroup(
            self,
            "WorkGroup",
            name=WORKGROUP,
            description="AeroPulse : analyses en lecture seule, volume analysé plafonné",
            recursive_delete_option=True,
            state="ENABLED",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                enforce_work_group_configuration=True,
                publish_cloud_watch_metrics_enabled=True,
                bytes_scanned_cutoff_per_query=ATHENA_SCAN_LIMIT_BYTES,
                engine_version=athena.CfnWorkGroup.EngineVersionProperty(
                    selected_engine_version="AUTO"
                ),
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{bucket_name}/athena-results/",
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3"
                    ),
                ),
            ),
        )
        for dimension in queries.DIMENSIONS:
            nq = athena.CfnNamedQuery(
                self,
                f"Stats{dimension.title()}",
                name=f"aeropulse-stats-{dimension}",
                description=f"Statistiques de retard par {dimension} (même SQL que l'API)",
                database=DATABASE,
                work_group=WORKGROUP,
                query_string=named_query_sql(dimension),
            )
            nq.node.add_dependency(workgroup)
            nq.node.add_dependency(table)

        cdk.CfnOutput(self, "DataBucketName", value=bucket_name)
        cdk.CfnOutput(self, "GlueDatabase", value=DATABASE)
        cdk.CfnOutput(self, "AthenaWorkGroup", value=WORKGROUP)
