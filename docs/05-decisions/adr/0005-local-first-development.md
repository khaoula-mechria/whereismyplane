# ADR-0005 — Développement local d'abord

- **Statut** : Acceptée (synthèse du projet)
- **Date** : 2026-11-05 (formalisation)

## Contexte

Les ressources AWS (SageMaker, Bedrock, base vectorielle) coûtent de l'argent et leurs itérations sont lentes. La plupart des erreurs de conception (fuite, variables, qualité de données) se trouvent sans AWS.

## Décision

Valider d'abord en local : ingestion, nettoyage, variables, modèles. Utiliser **Parquet + DuckDB** comme substitut d'Athena (mêmes fichiers, SQL portable). Activer AWS progressivement ([implementation-plan.md](../../03-project-management/implementation-plan.md), section 4). Point de contrôle **G3** : pas de dépense SageMaker avant que les modèles locaux battent la baseline.

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Tout construire directement sur AWS | Coût, lenteur, risque de découvrir tardivement un problème de données |
| Émulateurs AWS locaux complets | Complexité ; DuckDB suffit pour la partie SQL |

## Conséquences

- (+) Coût nul en phases A et B ; itérations rapides ; tests sans dépendance cloud.
- (−) Risque de divergence local/cloud : tests de parité (T6.3, T5.2, R-18).
