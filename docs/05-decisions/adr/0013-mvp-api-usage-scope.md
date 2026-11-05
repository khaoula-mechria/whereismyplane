# ADR-0013 — Périmètre d'usage de l'API en MVP

- **Statut** : Acceptée
- **Date** : 2026-11-05
- **Décisions couvertes** : D-02, D-05, D-09, D-13, D-16

## Décisions

| ID | Décision | Précisions |
|---|---|---|
| D-02 | Deux modes de prédiction : saisie manuelle des informations du vol **et** rejeu d'un vol de la période de test | La météo vient des données historiques disponibles à T-2h (donc conditionnée par D-01/[ADR-0009](0009-weather-at-t2h.md)). Si la reconstruction est impossible, le mode concerné est bloqué, pas simulé |
| D-05 | Pas de compte utilisateur en MVP | Clé d'API et limitation de débit pour protéger l'API et le budget |
| D-09 | Pas d'historique des prédictions | Aucune base de sessions ni de journal de prédictions ; l'historique de conversation reste côté client |
| D-13 | `generate_delay_report` produit du Markdown ou du JSON | PDF hors périmètre initial |
| D-16 | Seuil minimal de 30 vols pour afficher une statistique | En dessous : réponse « données insuffisantes » (AC-13) |

## Alternatives écartées

Cognito (reporté après le MVP), historique DynamoDB/S3, rapports PDF.

## Conséquences

- (+) Moins de composants, moins de coûts, moins de surface de sécurité.
- (−) Clé d'API visible côté client : protection limitée, compensée par la limitation de débit et le budget.
- Impacts : [api-design.md](../../02-architecture/api-design.md), [security-design.md](../../02-architecture/security-design.md), tâches T7.1 à T7.4, T8.3.
