# Composants du système

Chaque composant a une responsabilité unique, un emplacement dans le dépôt [Proposé] et des exigences associées. Vue graphique : [components.md](diagrams/components.md).

## Structure du dépôt cible [Proposé]

```
src/aeropulse/
  config.py      constantes : seuil 15 min, horizon 2 h, dates de découpage
  data/          ingestion, nettoyage, validation
  features/      variables T-2h, statistiques historiques, cibles
  models/        entraînement, évaluation, explicabilité
  analytics/     requêtes paramétrées (SQL) pour les statistiques
  tools/         les 7 outils de l'assistant + schémas d'entrée
  assistant/     boucle d'orchestration Bedrock, prompts
  api/           gestionnaires Lambda
pipelines/       glue/ et sagemaker/
infra/           application CDK, une stack par fichier
frontend/        application web
tests/
```

## Composants

| ID | Composant | Responsabilité | Entrées → Sorties | Technologie | Exigences |
|---|---|---|---|---|---|
| CMP-01 | Ingestion | Copier le jeu brut dans raw, vérifier le nombre de lignes | Fichier source → S3 raw | Python / script | FR-01 |
| CMP-02 | Nettoyage et validation | Doublons, valeurs manquantes, dates, contrôles de schéma | raw → processed (Parquet) | Glue PySpark ; version locale pandas/DuckDB | FR-02, NFR-08 |
| CMP-03 | Catalogue | Déclarer les tables et partitions | processed, analytics → tables Athena | Glue Data Catalog | FR-03 |
| CMP-04 | Agrégation analytique | Calculer agrégats par compagnie, aéroport, itinéraire avec taille d'échantillon | processed → analytics | Athena (CTAS) / Glue | FR-04 |
| CMP-05 | Ingénierie de variables | Variables T-2h, statistiques historiques ordonnées dans le temps, cibles | processed → ML dataset | Python partagé | FR-06, FR-07 |
| CMP-06 | Entraînement et évaluation | Entraîner 3 modèles par tâche, métriques, choix du seuil | ML dataset → modèles + rapport | scikit-learn, XGBoost ; SageMaker en cloud | FR-08 à FR-10 |
| CMP-07 | Explicabilité | Valeurs SHAP par prédiction et globales | modèle + entrée → contributions | SHAP | FR-11 |
| CMP-08 | Pipeline MLOps | Orchestrer préparation, entraînement, contrôle qualité, enregistrement | ML dataset → Model Registry | SageMaker Pipelines | FR-12 |
| CMP-09 | Endpoints d'inférence | Servir la classification (+ explications) | variables → prédiction | SageMaker | FR-13 |
| CMP-10 | Service d'analyse (outils) | Exécuter les requêtes prédéfinies, appliquer filtres, limites, seuil d'échantillon | paramètres validés → statistiques | Lambda + Athena | FR-15, FR-20 |
| CMP-11 | Service de prédiction | Valider l'entrée, construire les variables, appeler les endpoints, fusionner | requête → réponse de prédiction | Lambda | FR-14 |
| CMP-12 | Orchestrateur de l'assistant | Boucle LLM ↔ outils, bornée, journalisée ; modèle en paramètre de configuration (non choisi, ADR-0012) | question → réponse sourcée | Lambda + Bedrock | FR-19, FR-21 |
| CMP-13 | Générateur de rapport | Mettre en forme des résultats déjà calculés | résultats → rapport | Lambda (outil) | FR-22 |
| CMP-14 | Base de connaissances | Indexer et rechercher la documentation | docs S3 → passages | Bedrock Knowledge Bases | FR-23 (optionnel) |
| CMP-15 | API | Exposer routes, validation de forme, limitation de débit, CORS | HTTP → Lambda | API Gateway | FR-14, FR-15, FR-19 |
| CMP-16 | Frontend | Dashboard, formulaire, chat, avertissements | utilisateur ↔ API | SPA sur S3 + CloudFront | FR-16 à FR-18 |
| CMP-17 | Supervision | Logs, métriques, alertes, budget | tous composants → CloudWatch | CloudWatch, AWS Budgets | FR-24, NFR-04 |
| CMP-18 | Infrastructure | Décrire et déployer tout ce qui précède | code CDK → AWS | CDK | NFR-02 |

## Correspondance avec les stacks CDK

| Stack | Composants |
|---|---|
| `DataStack` | CMP-01 à CMP-04 (buckets, Glue, Athena workgroup) |
| `MLStack` | CMP-08, CMP-09 |
| `BackendStack` | CMP-10, CMP-11, CMP-13, CMP-15 |
| `AIStack` | CMP-12, CMP-14 (Bedrock, accès, base de connaissances) |
| `FrontendStack` | CMP-16 |
| `MonitoringStack` | CMP-17 |
| `NetworkStack` | Créée seulement si une ressource l'exige [Proposé] |

## Règles de dépendance entre modules

- `tools/` ne dépend ni de Bedrock ni de `api/` : testable seul.
- `features/` est utilisé par l'entraînement **et** par le service de prédiction (une seule implémentation).
- `assistant/` ne connaît que les schémas et noms d'outils, jamais le SQL.
- `analytics/` est le seul module qui contient du SQL.

## Interfaces entre composants

Contrats détaillés : [api-design.md](api-design.md) (HTTP), [database-design.md](database-design.md) (tables).
