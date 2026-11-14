# ADR-0004 — Découpage chronologique

- **Statut** : **Acceptée** — dates exactes approuvées le 2026-11-14 après mesure de la couverture réelle (D-17)
- **Date** : 2026-11-05 (mise à jour après adoption du dataset NYC 2023–2025, [ADR-0010](0010-dataset-nyc-2023-2025.md))

## Contexte

Un tirage aléatoire mélange passé et futur : les statistiques historiques et la météo d'un vol « fuient » vers ses voisins temporels, ce qui gonfle les métriques.

## Décision

Séparer train / validation / test **par ordre du temps** : le test est la période la plus récente, la validation la précède, l'entraînement vient en premier. Le test n'est utilisé qu'une fois pour l'évaluation finale ; seuil ([ADR-0015](0015-classification-threshold-selection.md)) et hyperparamètres se règlent sur la validation.

Le découpage est **adapté à la période réellement disponible** du dataset, pas à des dates figées a priori.

## Répartition cible (indicative)

| Jeu | Période visée |
|---|---|
| Entraînement | 2023 et une partie de 2024 |
| Validation | période ultérieure de 2024 |
| Test | 2025 |

**Dates retenues (2026-11-14)**, sur `flight_date` (heure locale), constantes dans `config.py` :

| Jeu | Période | Vols éligibles | Part |
|---|---|---|---|
| Entraînement | 2023-01-01 → 2024-06-30 | 621 512 | 60,5 % |
| Validation | 2024-07-01 → 2024-12-31 | 205 657 | 20,0 % |
| Test (une seule évaluation finale) | 2025-01-01 → 2025-07-31 | 200 417 | 19,5 % |

Limites : le test ne couvre que janvier–juillet ; un seul été (2023) en entraînement. Le texte ci-dessous est le raisonnement initial : les dates exactes sont fixées en **T3.6** après vérification de la couverture mensuelle réelle (juillet 2025 pourrait être partiel ; la période annoncée est janvier 2023 – juillet 2025, non vérifiée). Aucune date précise n'est décidée avant cette inspection. On examinera aussi la répartition en nombre de vols pour que validation et test aient une taille suffisante.

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Découpage aléatoire | Fuite temporelle |
| Validation croisée temporelle (expanding window) | Plus robuste mais plus coûteuse ; option pour renforcer la validation en WP4 |

## Conséquences

- (+) Simule l'usage sur des vols futurs ; 2,5 ans de données permettent de voir plusieurs saisons à l'entraînement.
- (−) Le test (2025, jusqu'à juillet environ) ne couvre pas une année complète : conclusions saisonnières limitées. Dérive possible entre 2023 et 2025 (R-03).
- Impacts : T3.6, AC-05, AC-06, AC-07.
