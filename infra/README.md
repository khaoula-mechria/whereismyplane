# infra — déploiement AWS de test (CDK Python)

Environnement `dev`, région `us-east-1`, budget 100 USD/mois. Architecture : [ADR-0018](../docs/05-decisions/adr/0018-aws-test-deployment-architecture.md) (**proposée**). **Aucun endpoint SageMaker** : le modèle est servi dans la Lambda.

```
poste local ──upload──▶ S3 raw/ ──▶ SageMaker Pipeline : Prepare ─▶ Train ─▶ Evaluate (D-22) ─▶ Register
                                         │                                              (approbation manuelle)
                                         ▼                                                       │
                          S3 processed/flights/ (Glue + Athena)                      EventBridge « Approved »
                                         │                                                       ▼
CloudFront ─┬─ /          ─▶ S3 (console de test)                     Lambda Promote ─▶ S3 releases/current.json
            └─ /v1/*      ─▶ API Gateway (clé + quota) ─▶ Lambda predict  ◀── bundle vérifié (SHA-256) ──┘
                                                       └▶ Lambda stats   ◀── processed/flights/
```

| Stack | Contenu |
|---|---|
| `AeroPulse-Data` | Bucket privé (raw, processed, runs, releases, athena-results), base et table Glue (projection de partitions), workgroup Athena plafonné à 1 Go/requête, 3 requêtes nommées |
| `AeroPulse-ML` | Image d'exécution (ECR), rôle SageMaker, groupe de modèles, pipeline `aeropulse-training`, promotion sur approbation |
| `AeroPulse-Backend` | Lambdas `predict` et `stats` (même image), API REST `/v1/{health,predict,meta,stats/{dimension}}`, clé d'API, 5 req/s, 2 000 req/jour ; **option** : Lambda `chat` et `POST /v1/chat` (assistant, 1 req/s) si un modèle Bedrock est fourni |
| `AeroPulse-Frontend` | Console de test (S3 privé + CloudFront), relais `/v1/*`, CSP stricte |
| `AeroPulse-Monitoring` | Budget 100 USD (50/80/100 % + prévision), 5 alarmes, contrôle quotidien des endpoints |

Non déployé par défaut : l'assistant `/v1/chat` (version de test, voir ci-dessous). Non construits : RAG (D-15), frontend React (T7.5–T7.7), suivi de dérive (FR-25).

## Prérequis (une fois)

1. **Identifiants AWS valides** sur le poste : `aws configure` avec une clé d'accès d'un utilisateur IAM, ou `aws configure sso`. Vérifier avec `uv run python scripts/aws/aeropulse_aws.py whoami`. Ne jamais mettre de clé dans le dépôt.
2. **Docker Desktop démarré** (construction de l'image linux/amd64, environ 2 Go).
3. Node.js ≥ 20 (`npx` télécharge la CLI CDK épinglée `aws-cdk@2.1147.0`).
4. Données locales présentes : `data/raw/`, `data/processed/flights/`, `data/ml/release/`, `data/serving/` (non versionnées).
5. Recommandé : mettre à jour l'AWS CLI (la version 2.0.30 installée date de 2020 et ne connaît pas SageMaker Pipelines ; les scripts utilisent boto3, pas la CLI).

## Déployer

```powershell
.\scripts\aws\deploy.ps1 -BudgetEmail "<votre adresse>"
```

Le script enchaîne : contrôles locaux (ruff, mypy, pytest, scan de secrets) → contexte d'image → `cdk bootstrap` → `cdk deploy --all` (confirmation demandée pour les changements IAM) → dépôt des données et du modèle local validé (`clf-f25ebbd328c5`) → test de fumée. Ensuite :

- **confirmer l'abonnement SNS** reçu par e-mail (sinon aucune alarme n'arrive) ;
- clé d'API : `uv run python scripts/aws/aeropulse_aws.py api-key` ;
- console : URL `SiteUrl` affichée par le test de fumée.

La première requête après un déploiement peut renvoyer 504 (démarrage à froid de l'image de 2 Go au-delà des 29 s d'API Gateway) ; la suivante répond normalement.

## Activer l'assistant (version de test, optionnel)

Le modèle Bedrock **n'est pas choisi** (ADR-0012) : vérifier d'abord sa disponibilité dans `us-east-1`, l'appel d'outils et le français (T8.1), puis activer l'accès au modèle dans la console Bedrock. Ensuite :

```powershell
npx --yes aws-cdk@2.1147.0 deploy AeroPulse-Backend AeroPulse-Monitoring -c budget_email="<adresse>" -c bedrock_model_id="<identifiant du modèle>"
```

Ce que cela ajoute : une Lambda `chat` (même image), `POST /v1/chat` limitée à 1 requête/s (rafale 2), le droit `bedrock:InvokeModel` sur **ce modèle seulement**, une alarme d'erreurs. L'orchestrateur borne la boucle d'outils (4 tours), les jetons de sortie (800) et la durée (24 s) ; il **retire toute réponse contenant un chiffre absent des résultats des outils** (`grounded: false`). Sans `bedrock_model_id`, rien de tout cela n'est synthétisé. Coût : à chiffrer selon le modèle retenu (voir [cost-estimate.md](../docs/04-quality/cost-estimate.md)).

## Cycle de réentraînement

```powershell
$ops = "scripts/aws/aeropulse_aws.py"
uv run python $ops start-pipeline          # ~quelques centimes (ml.m5.large)
uv run python $ops pipeline-status         # Prepare / Train / Evaluate / QualityGate / Register
uv run python $ops list-models             # paquets en PendingManualApproval
uv run python $ops approve <arn> --yes     # déclenche la promotion (journal : PromoteFunction)
uv run python $ops smoke-test              # model_versions reflète le modèle promu (≤ 5 min)
uv run python $ops rollback                # revient au pointeur précédent si besoin
```

Le contrôle D-22 de l'étape `Evaluate` porte sur la **validation** (le test a déjà servi, ADR-0004) et exécute les tests de non-fuite dans l'image. En échec, le pipeline s'arrête sur `QualityFailed` et rien n'est enregistré.

## Contrôler les coûts (fin de chaque session)

```powershell
uv run python scripts/aws/aeropulse_aws.py check-resources          # endpoints, jobs, NAT, volume S3
uv run python scripts/aws/aeropulse_aws.py check-resources --cost   # + coût du mois (Cost Explorer, 0,01 USD)
```

Code de sortie 1 si un endpoint SageMaker ou une passerelle NAT existe. Les alertes AWS Budgets **ne coupent pas** les dépenses.

## Détruire (AC-12)

```powershell
.\scripts\aws\destroy.ps1 -BudgetEmail "<votre adresse>"
```

Supprime les paquets du Model Registry, puis toutes les stacks (buckets vidés) et contrôle les ressources restantes. Restent hors de l'application : la stack `CDKToolkit` et son dépôt ECR d'actifs, les journaux `/aws/sagemaker/*`, l'historique des exécutions.

## Vérifier sans compte AWS

```powershell
uv run python scripts/build_lambda_context.py
npx --yes aws-cdk@2.1147.0 synth -q -c budget_email=ci@example.com
uv run pytest tests/test_infra.py tests/test_pipeline_definition.py
```

La synthèse et les tests d'assertions CDK tournent aussi en CI.
