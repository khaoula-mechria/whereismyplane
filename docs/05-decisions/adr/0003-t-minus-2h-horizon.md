# ADR-0003 — Horizon de prédiction T-2h et prévention des fuites

- **Statut** : Acceptée (synthèse du projet)
- **Date** : 2026-11-05 (formalisation)

## Contexte

Une prédiction n'a de sens que si elle n'utilise que ce qui est connu au moment où elle serait faite. Le jeu de données contient des champs réels (heures, retards) connus seulement après le départ.

## Décision

Prédire **2 heures avant l'heure de départ programmée**. Sont **interdits** : heure réelle de départ, retard réel au départ, heure et retard d'arrivée, toute information postérieure à T-2h (y compris observations météo postérieures). Les statistiques historiques ne portent que sur des vols dont le départ précède T-2h.

## Mise en œuvre

- Liste des colonnes interdites unique dans `config` (T0.5, T3.1).
- Colonne « disponible à T-2h ? » dans le dictionnaire de données (T1.3).
- Test automatique de non-fuite (T3.7, AC-03, AC-04).

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Prédire au moment du départ | Peu utile ; permettrait de lire des signaux déjà réalisés |
| Plusieurs horizons | Hors MVP ; extension possible |

## Conséquences

- (+) Évaluation réaliste, crédible.
- (−) Moins de signal que sans contrainte ; les métriques seront plus modestes mais honnêtes.
- Décision liée : [ADR-0009](0009-weather-at-t2h.md).
