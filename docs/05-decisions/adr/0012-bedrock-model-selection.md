# ADR-0012 — Choix du modèle Amazon Bedrock

- **Statut** : **En attente de vérification** — aucun modèle n'est choisi
- **Date** : 2026-11-05

## Contexte

L'assistant exige un modèle qui supporte le Tool Calling, répond correctement en français, et dont le coût tient dans le budget de 100 USD/mois. La région est `us-east-1` ([ADR-0011](0011-region-budget-cost-guardrails.md)). La liste des modèles disponibles, leurs tarifs et leurs fonctionnalités ne sont pas connus de ce dossier et ne doivent pas être supposés.

## Travail de vérification requis (T8.1)

| Critère | Comment vérifier |
|---|---|
| Disponibilité dans `us-east-1` (et nécessité d'activer l'accès) | Console Bedrock / documentation actuelle |
| Support du Tool Calling avec l'API utilisée (API Converse) | Documentation des fonctionnalités par modèle |
| Qualité en français et fiabilité d'usage des outils | Jeu d'évaluation du projet (T8.7) sur 2–3 candidats |
| Coût par jeton (entrée/sortie) et estimation mensuelle | Page tarifaire + [cost-estimate.md](../../04-quality/cost-estimate.md) |
| Quotas et limites de débit | Console Service Quotas |
| Latence | Mesure sur le jeu d'évaluation |
| Fonctionnalités RAG (Knowledge Bases, modèles d'embedding, magasins vectoriels disponibles dans la région) | Documentation ; nécessaire seulement si RAG retenu (D-15) |

## Décision

Reportée. Elle sera enregistrée ici (modèle retenu, alternatives comparées, justification, coût estimé) après la vérification. Le nom de modèle sera un **paramètre de configuration**, pas une constante du code.

## Conséquences

- La tâche T8.1 est un prérequis des tâches T8.5 à T8.8. Les outils (T8.2, T8.3) restent indépendants de Bedrock et peuvent avancer.
- Les estimations de coût Bedrock restent « à faire » jusqu'au choix.
