# Pile technologique

Statut : **C** = confirmé (synthèse) ; **T** = tranché par le propriétaire ; **P** = proposé, à approuver ; **V** = en attente de vérification. Région `us-east-1` ; la disponibilité de chaque service dans cette région est à vérifier avant déploiement (A-10). Budget : 100 USD/mois ([cost-estimate.md](../04-quality/cost-estimate.md)).

## Services AWS

| Domaine | Technologie | Statut | Rôle | Alternatives considérées |
|---|---|---|---|---|
| Stockage | Amazon S3 | C | Zones raw / processed / analytics, documents, frontend | — |
| Catalogue / ETL | AWS Glue (Data Catalog, jobs PySpark) | C | Schémas, transformations | Scripts Python/DuckDB seuls : probablement suffisants pour un volume de l'ordre du million de lignes (annoncé, non vérifié) ; Glue/PySpark conservé car confirmé, avec un coût d'exécution à estimer (voir note) |
| SQL | Amazon Athena | C | Statistiques et requêtes | Redshift, RDS |
| ML | Amazon SageMaker (Pipelines, Model Registry, endpoints) | C | Entraînement, registre, inférence | Entraînement local + déploiement Lambda |
| API | API Gateway (REST ou HTTP) | C | Exposition, clé d'API et limitation de débit (D-05) | — ; type d'API à choisir en T6.5 selon la prise en charge des clés d'API et plans d'utilisation (à vérifier dans la documentation) |
| Backend | AWS Lambda (Python) | C | Validation, orchestration, outils | Conteneurs (ECS) : non justifié |
| LLM | Amazon Bedrock | C | Raisonnement, choix d'outils, rédaction | — ; **modèle non choisi (V)**, voir [ADR-0012](../05-decisions/adr/0012-bedrock-model-selection.md) |
| RAG | Bedrock Knowledge Bases | C, si retenu | Recherche documentaire | Index maison sur S3 ; magasin vectoriel décidé à l'étape 9 (D-15) ; voir note coût |
| Frontend | S3 + CloudFront | C | Hébergement statique | — |
| Supervision | CloudWatch (+ Model Monitor en option) | C | Logs, métriques, alertes | — |
| Sécurité | IAM, chiffrement, Secrets Manager si nécessaire | C | Accès, secrets | — |
| Coûts | AWS Budgets (50 %, 80 %, 100 % de 100 USD), Cost Explorer | T | Alertes de dépense (sans arrêt automatique garanti) | — |
| IaC | AWS CDK (Python) | T | Stacks versionnées | Terraform, CDK TypeScript |

**Note Glue** : pour ce volume, pandas ou DuckDB suffiraient techniquement. Glue/PySpark est conservé car il fait partie du périmètre confirmé (Data Engineering), mais le travail de transformation sera d'abord écrit et validé en local ([ADR-0005](../05-decisions/adr/0005-local-first-development.md)).

**Note RAG** : le magasin vectoriel associé à une Knowledge Base peut avoir un coût de base notable selon l'option choisie. À vérifier dans la documentation AWS actuelle avant l'étape 9 (R-11).

## Langages et bibliothèques (proposé)

| Domaine | Choix | Statut |
|---|---|---|
| Langage principal | Python 3.11 ou 3.12 (aligné sur le runtime Lambda disponible, à vérifier) | P |
| Dépendances | uv | T (D-11) |
| Données locales | pandas ou polars, PyArrow, DuckDB | P |
| Qualité des données | Contrôles écrits maison ou Great Expectations/pandera | ? (pandera proposé : léger) |
| ML | scikit-learn, XGBoost | C (algorithmes) |
| Explicabilité | SHAP (TreeExplainer pour les modèles d'arbres) | C |
| Suivi d'expériences | Local : fichiers/MLflow optionnel ; cloud : SageMaker Experiments | ? |
| Tests | pytest, moto ou stubs pour AWS, tests de snapshot CDK | P |
| Qualité du code | ruff, mypy (ou pyright), pre-commit | P |
| CDK | Python | T (D-03) |
| Frontend | React + Vite (SPA) + bibliothèque de graphiques légère (choix précis en T7.5) ; interface en français | T (D-04) |
| CI | GitHub Actions avec authentification OIDC vers AWS (pas de clés longues) | P |

## Pourquoi pas…

| Technologie | Raison de l'écarter pour le MVP |
|---|---|
| Streamlit | Nécessite un serveur ; incompatible avec l'hébergement S3 + CloudFront confirmé |
| Redshift | Coût et administration injustifiés pour ce volume |
| Kinesis / Firehose | Hors MVP (extension flux) |
| Cognito | Pas de comptes utilisateurs en MVP (D-05) |
| NAT Gateway / VPC endpoints | Facturation continue, inutile au MVP (C-08, budget) |
| VPC dédié | Non nécessaire (C-08) ; à revoir si une ressource l'exige |

## Versions

Les versions exactes sont fixées dans le fichier de verrouillage du gestionnaire de dépendances à l'étape WP0. Aucune version n'est affirmée ici.
