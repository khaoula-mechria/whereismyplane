# ADR-0015 — Choix du seuil de classification

- **Statut** : Acceptée
- **Date** : 2026-11-05
- **Décision couverte** : D-08

## Contexte

Le modèle de classification produit une probabilité de retard > 15 minutes. La décision binaire dépend d'un seuil. Le seuil par défaut de 0,5 est rarement adapté à une classe minoritaire.

## Décision

Choisir le seuil à partir des résultats de **validation** (jamais du test), en **privilégiant le F1-score** et en **examinant également le rappel** (Recall) et la précision. Le seuil retenu, la courbe précision/rappel et la justification sont consignés dans le rapport de modélisation (T4.5). La probabilité brute reste affichée avec la décision.

## Alternatives écartées

Seuil fixe à 0,5 ; optimisation sur le jeu de test (fuite d'information).

## Conséquences

- (+) Seuil défendable et reproductible.
- (−) Dépend de la période de validation : à recontrôler si la distribution change (dérive).
- Impacts : FR-10, AC-07, T4.5, réponse de `/predict` (champ `threshold`).
