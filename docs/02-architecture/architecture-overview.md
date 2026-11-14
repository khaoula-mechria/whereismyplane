# Vue d'ensemble de l'architecture

Projet **AeroPulse** (anciennement FlightWise). Statut : **[Confirmé]** pour les choix de la synthèse et les décisions arbitrées (D-01 à D-17, voir [decisions-pending.md](../05-decisions/decisions-pending.md)) ; **[Proposé]** pour les compléments non encore arbitrés ; **[À vérifier]** pour ce qui dépend d'une vérification technique (dataset, météo T-2h, modèle Bedrock, coûts).

Cadre : région AWS `us-east-1`, budget maximal 100 USD/mois ([ADR-0011](../05-decisions/adr/0011-region-budget-cost-guardrails.md)), dataset NYC Flight Delays and Weather 2023–2025 ([ADR-0010](../05-decisions/adr/0010-dataset-nyc-2023-2025.md)).

## 1. Style d'architecture

Architecture **serverless orientée données**, en trois couches :

1. **Données** : lac S3 (raw / processed / analytics) + Glue (catalogue, ETL) + Athena (SQL).
2. **ML** : entraînement et inférence SageMaker, un modèle de classification (la régression est reportée, ADR-0017).
3. **Application** : API Gateway + Lambda, frontend statique S3 + CloudFront, assistant Bedrock.

L'IA générative suit l'**approche hybride** [Confirmé, [ADR-0001](../05-decisions/adr/0001-hybrid-tool-calling-rag.md)] :

| Voie | Quand | Source de vérité |
|---|---|---|
| Tool Calling | Statistiques, prédiction, explication, rapport | Athena et SageMaker |
| RAG (optionnel) | Définitions, documentation, méthodologie | Documents du projet |

## 2. Diagrammes

| Diagramme | Fichier |
|---|---|
| Contexte système | [context.md](diagrams/context.md) |
| Conteneurs | [containers.md](diagrams/containers.md) |
| Composants du backend | [components.md](diagrams/components.md) |
| Flux de données | [dataflow.md](diagrams/dataflow.md) |
| Modèle de données (ER) | [er-diagram.md](diagrams/er-diagram.md) |
| Séquences | [sequences.md](diagrams/sequences.md) |

## 3. Alternatives étudiées

| Décision | Choix retenu | Alternatives | Raison |
|---|---|---|---|
| Entrepôt analytique | S3 + Glue + Athena | Redshift ; RDS/PostgreSQL | Pas de serveur à gérer, coût à la requête, volume modeste. Réévaluer si volume ou fréquence augmentent ([ADR-0002](../05-decisions/adr/0002-s3-glue-athena-parquet.md)) |
| Hébergement des modèles | Un endpoint SageMaker **temporaire** (D-07, ADR-0017) | Un endpoint multi-modèles ; inférence serverless (à évaluer, T5.7) ; modèle embarqué dans Lambda | Séparation claire, MLOps cohérent ; endpoints supprimés hors démonstration pour tenir 100 USD/mois ([ADR-0007](../05-decisions/adr/0007-sagemaker-two-endpoints.md)) |
| Intégration du LLM | Tool Calling + RAG | RAG seul ; SQL généré par le LLM | Fiabilité des chiffres, contrôle des accès ([ADR-0008](../05-decisions/adr/0008-llm-no-free-sql.md)) |
| Orchestration de l'agent | Boucle d'outils dans Lambda (API Converse de Bedrock) [Proposé] | Bedrock Agents ; framework tiers | Contrôle total, tests locaux, peu de dépendances. Bedrock Agents reste une option si la boucle devient complexe |
| Frontend | SPA React + Vite sur S3 + CloudFront (D-04) | Hébergement serveur (ECS/Amplify) | Moins cher, plus simple (voir [technology-stack.md](technology-stack.md)) |
| IaC | CDK en Python (D-03) | Terraform ; CloudFormation brut | Choix tranché ([ADR-0006](../05-decisions/adr/0006-cdk-infrastructure-as-code.md)) |
| Accès à l'API | Clé d'API + limitation de débit, sans comptes (D-05) | Cognito | Simplicité et coût ; protection limitée ([ADR-0013](../05-decisions/adr/0013-mvp-api-usage-scope.md)) |

## 4. Choix transverses

- **Environnements** : un seul environnement `dev` AWS (`us-east-1`), plus le local ; un `prod` n'est pas justifié pour un MVP [Proposé].
- **Contrôle des coûts** : aucune ressource payante avant l'estimation approuvée ([cost-estimate.md](../04-quality/cost-estimate.md), point G0) ; AWS Budgets à 50/80/100 % n'arrête pas les dépenses, d'où une vérification régulière des ressources actives.
- **Pas d'historique de prédictions** : aucune base de données applicative en MVP (D-09).
- **Parité local / cloud** : mêmes fichiers Parquet, requêtes SQL écrites dans le dialecte commun à DuckDB et Athena (Trino) autant que possible [Proposé].
- **Outils indépendants de Bedrock** : fonctions Python pures + schémas d'entrée ; Bedrock ne fait que les appeler [Proposé].
- **Pas de base transactionnelle** en MVP : aucune donnée utilisateur à gérer [Hypothèse A-05, A-06] ([database-design.md](database-design.md)).
- **Réseau minimal** : services managés accessibles par IAM ; pas de VPC sauf nécessité avérée [Confirmé C-08].

## 5. Points de vigilance techniques

| Sujet | Risque | Réponse |
|---|---|---|
| Limite d'intégration d'API Gateway (≈ 29 s par défaut, à vérifier) | La boucle d'outils du chat peut dépasser | Limiter à N itérations d'outils, réponses courtes, délais d'expiration par outil ([risk-register.md](../03-project-management/risk-register.md) R-12) |
| Démarrage à froid Lambda et endpoints | Latence à la première requête | Mesurer ; accepter pour le MVP, documenter |
| Calcul SHAP | Où l'exécuter ? | Tranché (D-06) : dans le script d'inférence SageMaker |
| Cohérence des variables entre entraînement et inférence | Biais d'entraînement/service | Une seule bibliothèque de variables partagée par l'entraînement et le backend |
| Météo à T-2h | Horodatages peut-être inexploitables ; décalage entre entraînement et usage | [ADR-0009](../05-decisions/adr/0009-weather-at-t2h.md) (acceptée sous condition), [dataset-card.md](../dataset-card.md) |
| Modèle Bedrock | Disponibilité, Tool Calling, coût en `us-east-1` | [ADR-0012](../05-decisions/adr/0012-bedrock-model-selection.md) (en attente de vérification) |
| Budget | Dépassement de 100 USD/mois | [cost-estimate.md](../04-quality/cost-estimate.md), R-05 |

## 6. Traçabilité

Composants détaillés : [system-components.md](system-components.md). Sécurité : [security-design.md](security-design.md). Déploiement : [deployment-strategy.md](../04-quality/deployment-strategy.md).
