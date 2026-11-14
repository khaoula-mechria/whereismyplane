# Architecture Decision Records

Une ADR par décision structurante : contexte, décision, alternatives, conséquences. Statuts : **Acceptée**, **Acceptée sous condition**, **En attente de vérification**, **Remplacée**.

| ADR | Titre | Statut | Décisions |
|---|---|---|---|
| [0001](0001-hybrid-tool-calling-rag.md) | Approche hybride Tool Calling + RAG | Acceptée | D-15 (principe) |
| [0002](0002-s3-glue-athena-parquet.md) | S3 + Glue + Athena + Parquet plutôt que Redshift | Acceptée | — |
| [0003](0003-t-minus-2h-horizon.md) | Horizon T-2h et prévention des fuites | Acceptée | — |
| [0004](0004-chronological-split.md) | Découpage chronologique | Acceptée (dates approuvées le 2026-11-14) | D-17 |
| [0005](0005-local-first-development.md) | Développement local d'abord | Acceptée | — |
| [0006](0006-cdk-infrastructure-as-code.md) | AWS CDK en Python | Acceptée | D-03 |
| [0007](0007-sagemaker-two-endpoints.md) | Deux modèles, deux endpoints temporaires, SHAP à l'inférence | Acceptée (serverless à évaluer) ; **modifiée par 0017 : un seul endpoint** | D-06, D-07 |
| [0008](0008-llm-no-free-sql.md) | Pas de SQL libre pour le LLM | Acceptée | — |
| [0009](0009-weather-at-t2h.md) | Météo disponible à T-2h (option A) | **Acceptée sous condition** (horodatages à vérifier) | D-01 |
| [0010](0010-dataset-nyc-2023-2025.md) | Dataset NYC 2023–2025 | Acceptée (caractéristiques et licence à vérifier) | — |
| [0011](0011-region-budget-cost-guardrails.md) | us-east-1, budget 100 USD/mois, garde-fous | Acceptée (estimation requise avant déploiement) | D-12 (région, budget) |
| [0012](0012-bedrock-model-selection.md) | Choix du modèle Bedrock | **En attente de vérification** | D-12 (modèle) |
| [0013](0013-mvp-api-usage-scope.md) | Périmètre d'usage de l'API en MVP | Acceptée | D-02, D-05, D-09, D-13, D-16 |
| [0014](0014-development-tooling.md) | uv, React + Vite | Acceptée | D-04, D-11 |
| [0015](0015-classification-threshold-selection.md) | Choix du seuil de classification | Acceptée | D-08 |
| [0016](0016-dataset-acquisition-strategy.md) | Stratégie d'acquisition du dataset (reconstruction BTS + NOAA) | Acceptée (licences à lire avant téléchargement complet) | D-18, D-19 |
| [0017](0017-regression-postponed.md) | Régression reportée : classification seule pour l'instant | Acceptée | D-21 |

D-10 (objectifs de latence) et D-14 (documents de pilotage) n'ont pas d'ADR : voir [decisions-pending.md](../decisions-pending.md).

Nouvelle ADR : copier la structure d'une ADR existante, numéroter à la suite, ajouter une ligne ici.
