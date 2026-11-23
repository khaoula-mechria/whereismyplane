<#
.SYNOPSIS
  Supprime l'environnement de test AeroPulse (AC-12) puis contrôle les ressources restantes.

.DESCRIPTION
  1. Supprime les paquets du Model Registry (sinon CloudFormation ne peut pas supprimer le groupe).
  2. cdk destroy --all (CDK demande confirmation) : buckets vidés et supprimés, Lambdas, API,
     CloudFront, pipeline, budget, alarmes.
  3. check-resources : aucun endpoint, aucun job en cours, aucune passerelle NAT.

  Restent après destruction (hors de l'application, à supprimer à la main si souhaité) :
  la stack CDKToolkit et son dépôt ECR d'actifs (images, ~0,10 USD/Go-mois), les groupes de
  journaux /aws/sagemaker/* créés par SageMaker, l'historique des exécutions SageMaker.

.EXAMPLE
  .\scripts\aws\destroy.ps1 -BudgetEmail "moi@exemple.org"
#>
param([Parameter(Mandatory = $true)][string]$BudgetEmail)

$ErrorActionPreference = "Stop"
$Cdk = "aws-cdk@2.1147.0"
$Ops = "scripts/aws/aeropulse_aws.py"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
$env:AEROPULSE_BUDGET_EMAIL = $BudgetEmail

uv run python $Ops cleanup-registry --yes
if ($LASTEXITCODE -ne 0) { throw "Échec du nettoyage du Model Registry" }

# La synthèse a besoin du contexte de l'image (aucune construction n'a lieu à la destruction).
uv run python scripts/build_lambda_context.py
npx --yes $Cdk destroy --all -c "budget_email=$BudgetEmail"
if ($LASTEXITCODE -ne 0) { throw "Échec de cdk destroy" }

uv run python $Ops check-resources
