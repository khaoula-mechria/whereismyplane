# ADR-0007 — Deux modèles, deux endpoints SageMaker

- **Statut** : Acceptée — deux endpoints (synthèse), SHAP dans l'inférence (D-06 tranchée), endpoints temporaires (D-07 tranchée). L'**évaluation de l'inférence serverless** reste à faire (T5.7)
- **Date** : 2026-11-05 (formalisation)

## Contexte

Deux tâches (classification, régression) à servir. Un endpoint temps réel permanent coûte en continu, même sans trafic.

## Décision

Un endpoint de classification et un de régression, enregistrés dans le Model Registry et déployés après approbation manuelle. Les endpoints sont **éphémères** : créés pour tests et démonstrations, supprimés ensuite (C-09).

## Options d'hébergement comparées

| Option | Avantage | Inconvénient |
|---|---|---|
| Deux endpoints temps réel (retenu) | Séparation nette, MLOps cohérent | Coût continu tant qu'ils existent |
| Inférence serverless | Pas de coût à l'arrêt | Démarrage à froid ; limites de taille/conteneur à vérifier |
| Un seul endpoint (multi-modèles ou modèle combiné) | Moins de ressources | Couplage ; moins lisible |
| Modèle embarqué dans Lambda | Très économique | Sort du périmètre SageMaker confirmé |

## Décisions annexes (approuvées)

- **SHAP calculé dans le script d'inférence SageMaker** (D-06) : les explications correspondent exactement au modèle servi.
- **Endpoints temps réel activés temporairement** pendant les démonstrations et tests (D-07), pour tenir le budget de 100 USD/mois ([ADR-0011](0011-region-budget-cost-guardrails.md)). **L'évaluation de l'inférence serverless** pour réduire les coûts reste à faire en T5.7 ; ses limites et son coût réel ne sont pas supposés ici.

## Conséquences

- (+) Architecture conforme à la synthèse, coûts maîtrisés par le cycle de vie.
- (−) Le service est indisponible quand les endpoints sont supprimés : `503 model_unavailable` explicite et procédure de démonstration ([deployment-strategy.md](../../04-quality/deployment-strategy.md)).
