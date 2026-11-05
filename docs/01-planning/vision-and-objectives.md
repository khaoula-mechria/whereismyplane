# Vision et objectifs

## Vision

Rendre le risque de retard d'un vol **mesurable, explicable et interrogeable en langage naturel**, avec une chaîne technique entièrement reproductible sur AWS.

## Principes directeurs [Confirmé]

| # | Principe | Conséquence concrète |
|---|---|---|
| P1 | Les chiffres viennent des données et des modèles, jamais du LLM | Tool Calling avec requêtes prédéfinies ([ADR-0001](../05-decisions/adr/0001-hybrid-tool-calling-rag.md), [ADR-0008](../05-decisions/adr/0008-llm-no-free-sql.md)) |
| P2 | Aucune information postérieure à T-2h dans les variables | Contrat de variables + test de fuite ([ADR-0003](../05-decisions/adr/0003-t-minus-2h-horizon.md)) |
| P3 | Évaluer comme on utilisera : sur le futur | Découpage chronologique ([ADR-0004](../05-decisions/adr/0004-chronological-split.md)) |
| P4 | Valider en local avant de payer AWS | Parquet + DuckDB en local ([ADR-0005](../05-decisions/adr/0005-local-first-development.md)) |
| P5 | Dire ce que les données ne permettent pas de dire | Avertissements dans l'interface : période, aéroports, SHAP ≠ causalité |
| P6 | Ne rien inventer | Pas de donnée, de résultat, de coût ni de configuration fabriqués ; en cas d'impossibilité (ex. météo à T-2h), on signale le blocage |

## Objectifs SMART

| ID | Objectif | Mesure | Priorité |
|---|---|---|---|
| OBJ-1 | Construire un lac de données S3/Glue/Athena fiable | Tables cataloguées, requêtables, contrôles qualité passés | MVP |
| OBJ-2 | Prédire le risque et la durée du retard à T-2h | Modèles battant la baseline sur le jeu de test chronologique | MVP |
| OBJ-3 | Expliquer chaque prédiction | Top-k contributions SHAP renvoyées avec la prédiction | MVP |
| OBJ-4 | Fournir des statistiques par compagnie, aéroport, itinéraire | Dashboard + outils de l'assistant, avec période et taille d'échantillon | MVP |
| OBJ-5 | Proposer un assistant fiable | Taux de chiffres vérifiables = 100 % sur le jeu d'évaluation | MVP |
| OBJ-6 | Déployer par code et maîtriser les coûts | CDK deploy/destroy ; endpoints temporaires ; dépense ≤ 100 USD/mois ; estimation approuvée avant déploiement | MVP |
| OBJ-7 | Répondre aux questions documentaires | RAG sur la documentation du projet | Optionnel |
| OBJ-8 | Superviser | Logs, métriques, alertes de base ; dérive en option | Optionnel |

## Hors objectifs

- Prédire les conditions réelles actuelles (aucune donnée récente).
- Remplacer un système opérationnel de compagnie ou d'aéroport.
- Établir des relations causales entre météo et retards.

## Liens

[project-brief.md](project-brief.md) · [requirements.md](requirements.md) · [implementation-plan.md](../03-project-management/implementation-plan.md)
