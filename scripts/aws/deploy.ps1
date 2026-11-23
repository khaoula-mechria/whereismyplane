<#
.SYNOPSIS
  Déploie l'environnement de test AeroPulse (us-east-1) de bout en bout.

.DESCRIPTION
  1. Préalables : identifiants AWS valides, Docker démarré, Node.js présent.
  2. Contrôles locaux : ruff, mypy, pytest (dont tests de non-fuite), scan de secrets.
  3. Contexte de l'image d'exécution (scripts/build_lambda_context.py).
  4. cdk bootstrap (idempotent) puis cdk deploy --all (l'image est construite et poussée).
  5. Données : raw/ (pour le pipeline), processed/ (pour /v1/stats), bundle du modèle local.
  6. Test de fumée des routes déployées.
  Option -RunPipeline : lance aussi une exécution du pipeline SageMaker (quelques centimes).

  Coût : voir docs/04-quality/cost-estimate.md. Aucun endpoint SageMaker n'est créé.
  Ne jamais committer l'adresse e-mail : elle est passée en paramètre, pas écrite dans le dépôt.

.EXAMPLE
  .\scripts\aws\deploy.ps1 -BudgetEmail "moi@exemple.org"
#>
param(
    [Parameter(Mandatory = $true)][string]$BudgetEmail,
    [switch]$SkipChecks,
    [switch]$RunPipeline
)

$ErrorActionPreference = "Stop"
$Cdk = "aws-cdk@2.1147.0"
$Ops = "scripts/aws/aeropulse_aws.py"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
$env:AEROPULSE_BUDGET_EMAIL = $BudgetEmail

function Invoke-Step {
    param([string]$Name, [scriptblock]$Block)
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) { throw "Échec : $Name (code $LASTEXITCODE)" }
}

Invoke-Step "Identité AWS" { uv run python $Ops whoami }
$identity = (uv run python $Ops whoami) | ConvertFrom-Json
$account = $identity.account

Invoke-Step "Docker démarré" { docker info --format "{{.ServerVersion}}" }

if (-not $SkipChecks) {
    Invoke-Step "Lint" { uv run ruff check }
    Invoke-Step "Typage" { uv run mypy }
    Invoke-Step "Tests (dont non-fuite)" { uv run pytest -q }
    Invoke-Step "Scan de secrets" { uv run python scripts/check_secrets.py }
}

Invoke-Step "Contexte de l'image" { uv run python scripts/build_lambda_context.py }
Invoke-Step "CDK bootstrap aws://$account/us-east-1" {
    npx --yes $Cdk bootstrap "aws://$account/us-east-1" -c "budget_email=$BudgetEmail"
}
# --require-approval broadening : CDK demande confirmation pour tout élargissement IAM.
Invoke-Step "CDK deploy (5 stacks)" {
    npx --yes $Cdk deploy --all --require-approval broadening -c "budget_email=$BudgetEmail" `
        --outputs-file cdk.out/outputs.json
}

Invoke-Step "Données brutes -> raw/" { uv run python $Ops upload-raw }
Invoke-Step "Parquet préparé -> processed/flights/" { uv run python $Ops upload-processed }
Invoke-Step "Bundle du modèle local -> releases/" { uv run python $Ops publish-local-bundle }
Invoke-Step "Test de fumée" { uv run python $Ops smoke-test }

if ($RunPipeline) {
    Invoke-Step "Pipeline SageMaker" { uv run python $Ops start-pipeline }
    Write-Host "Suivi : uv run python $Ops pipeline-status"
}

Write-Host "`nDéployé. Confirmer l'abonnement SNS reçu par e-mail (alertes)." -ForegroundColor Green
Write-Host "Clé d'API : uv run python $Ops api-key"
Write-Host "Ressources facturables : uv run python $Ops check-resources"
