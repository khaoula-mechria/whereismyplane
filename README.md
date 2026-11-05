# AeroPulse (whereismyplane)

> Anciennement nommé **FlightWise**. Le dépôt s'appelle `whereismyplane`.

Plateforme d'analyse et de prédiction des retards de vols, combinant **Data Engineering, Machine Learning, MLOps, AWS et IA générative**.

> **Statut : phase de planification.** Aucun code applicatif n'est encore écrit. Les décisions D-01 à D-17 ont été arbitrées ; plusieurs vérifications techniques restent en attente (voir [decisions-pending.md](docs/05-decisions/decisions-pending.md)).

## Ce que fait AeroPulse

- Prédit si un vol aura plus de 15 minutes de retard au départ, et estime le retard en minutes, **2 heures avant le départ programmé (T-2h)**.
- Explique les prédictions avec SHAP (influence, pas causalité).
- Fournit des statistiques par compagnie, aéroport et itinéraire.
- Offre un assistant conversationnel (Amazon Bedrock) qui s'appuie sur des outils contrôlés (Tool Calling) et, en option, sur la documentation du projet (RAG).
- Interface en français (principale) ; l'anglais pourra être ajouté ensuite.

## Données et limites

Dataset principal retenu : **NYC Flight Delays and Weather (2023–2025)**, annoncé avec environ 1 056 897 vols, 33 variables, les aéroports JFK, EWR et LGA, de janvier 2023 à juillet 2025. **Ces caractéristiques sont annoncées, non vérifiées** : elles seront contrôlées sur le fichier réel (voir [dataset-card.md](docs/dataset-card.md)). La licence et la source exacte restent à documenter.

Les prédictions reposent sur des données historiques : elles ne décrivent **pas** les conditions actuelles.

## Architecture en bref

S3 + Glue + Athena (données) → SageMaker (classification et régression) → API Gateway + Lambda → frontend React (S3 + CloudFront) → assistant Bedrock. Infrastructure en AWS CDK (Python), région `us-east-1`, **budget maximal 100 USD/mois**. Développement **local d'abord**, AWS ensuite, après estimation des coûts.

## Documentation

Tout est dans [docs/](docs/README.md) :

| Pour… | Voir |
|---|---|
| Comprendre le projet | [project-brief](docs/01-planning/project-brief.md) |
| Voir l'architecture | [architecture-overview](docs/02-architecture/architecture-overview.md) |
| Connaître le plan et les tâches | [implementation-plan](docs/03-project-management/implementation-plan.md), [task-breakdown](docs/03-project-management/task-breakdown.md) |
| Connaître le dataset | [dataset-card](docs/dataset-card.md), [data-dictionary](docs/data-dictionary.md) |
| Maîtriser les coûts | [cost-estimate](docs/04-quality/cost-estimate.md) |
| Savoir où en est le projet | [PROGRESS](docs/PROGRESS.md) |
| Voir les décisions et blocages | [decisions-pending](docs/05-decisions/decisions-pending.md) |

## Prochaines étapes

Voir [docs/PROGRESS.md](docs/PROGRESS.md). En résumé : fondations (WP0) sans ressource AWS payante, puis obtention et inspection du dataset (WP1).
