"""Constantes de déploiement communes à la CDK et à ``scripts/aws`` (sans import CDK)."""

from __future__ import annotations

REGION = "us-east-1"  # ADR-0011
PROJECT = "aeropulse"
ENVIRONMENT = "dev"
STACK_PREFIX = "AeroPulse"
STACKS = {
    "data": f"{STACK_PREFIX}-Data",
    "ml": f"{STACK_PREFIX}-ML",
    "backend": f"{STACK_PREFIX}-Backend",
    "frontend": f"{STACK_PREFIX}-Frontend",
    "monitoring": f"{STACK_PREFIX}-Monitoring",
}
MODEL_PACKAGE_GROUP = "aeropulse-delay-classifier"
BUNDLE_POINTER_KEY = "releases/current.json"
PREVIOUS_POINTER_KEY = "releases/previous.json"
PROCESSED_PREFIX = "processed/flights/"
RAW_PREFIX = "raw/"
CDK_CLI = "aws-cdk@2.1147.0"  # version épinglée, compatible avec aws-cdk-lib 2.275.0
