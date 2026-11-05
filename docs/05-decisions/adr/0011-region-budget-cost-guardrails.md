# ADR-0011 — Région us-east-1, budget de 100 USD/mois et garde-fous de coût

- **Statut** : Acceptée — **estimation de coûts à produire avant tout déploiement payant (point G0)**
- **Date** : 2026-11-05

## Contexte

Le propriétaire fixe la région AWS `us-east-1` et un budget mensuel maximal de 100 USD pour le développement et les démonstrations. La date limite et la taille de l'équipe restent inconnues.

## Décision

1. Région unique : `us-east-1` (N. Virginia). La disponibilité réelle de chaque service et du modèle Bedrock dans cette région reste à vérifier avant usage ([ADR-0012](0012-bedrock-model-selection.md)).
2. Budget maximal : **100 USD/mois**.
3. **AWS Budgets** avec alertes à **50 %, 80 % et 100 %**. Ces alertes **ne garantissent pas l'arrêt des dépenses**.
4. Aucune ressource payante déployée avant l'estimation de [cost-estimate.md](../../04-quality/cost-estimate.md) et son approbation.
5. Ressources coûteuses toujours actives interdites : endpoints SageMaker temporaires (D-07), pas de NAT Gateway, RAG optionnel.
6. Vérification régulière des ressources actives (checklist de cost-estimate.md), consignée dans PROGRESS.md.
7. Toute fonctionnalité susceptible de dépasser le budget est signalée avant sa mise en œuvre.

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Plusieurs régions | Complexité et coût inutiles |
| Compter sur les alertes comme protection | Elles notifient, ne bloquent pas |
| Région non figée | Le propriétaire a désormais tranché |

## Conséquences

- (+) Cadre financier explicite, tâches T0.6 (budgets) et T0.8 (estimation) ajoutées.
- (−) Le budget contraint : pas d'endpoint permanent, RAG sous conditions, assistant à jetons plafonnés.
- Si l'estimation pessimiste dépasse 100 USD, l'architecture est révisée avant déploiement (par exemple inférence serverless, réduction du RAG).
- Risque lié : R-05.
