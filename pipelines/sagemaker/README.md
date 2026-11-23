# pipelines/sagemaker

Définition du pipeline SageMaker `aeropulse-training` ([pipeline.py](pipeline.py)) : JSON construit sans SDK SageMaker, déployé par `infra/stacks/ml_stack.py` ([ADR-0018](../../docs/05-decisions/adr/0018-aws-test-deployment-architecture.md), proposée).

| Étape | Type | Code exécuté (image d'exécution) |
|---|---|---|
| `Prepare` | Processing | `aeropulse.mlops.prepare_job` → `data.pipeline`, `features.build`, `data.serving_tables` |
| `Train` | Training | `aeropulse.mlops.train_job` → `models.final`, `models.release`, bundle de service |
| `Evaluate` | Processing | `aeropulse.mlops.evaluate_job` → contrôle D-22 sur la validation + tests de non-fuite |
| `QualityGate` | Condition | `quality.passed_flag == 1` |
| `Register` / `QualityFailed` | RegisterModel / Fail | Model Registry, **approbation manuelle** |

Aucune étape ne crée d'endpoint. Vérifié en local le 2026-11-21 : la chaîne reproduit à l'identique le modèle `clf-f25ebbd328c5`.
