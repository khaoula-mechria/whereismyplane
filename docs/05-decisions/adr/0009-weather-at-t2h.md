# ADR-0009 — Météo disponible à T-2h

- **Statut** : Acceptée **sous condition** (D-01 tranchée : option A) — **en attente de vérification technique des horodatages météo du dataset**
- **Date** : 2026-11-05

## Contexte

La synthèse précise que les observations météo postérieures à T-2h ne doivent pas remplacer une prévision disponible à T-2h. Le dataset NYC 2023–2025 est annoncé avec des « informations météorologiques associées » ; leur granularité et leurs horodatages sont **inconnus** ([dataset-card.md](../../dataset-card.md)).

## Options étudiées

| Option | Description | Avantage | Inconvénient |
|---|---|---|---|
| A. Dernière observation avant T-2h | Joindre l'observation la plus récente dont l'heure est ≤ T-2h | Pas de fuite, réaliste | Moins informatif qu'une prévision ; nécessite des horodatages exploitables |
| B. Météo observée au départ | Observation proche du départ | Plus de signal | **Fuite** : contraire à [ADR-0003](0003-t-minus-2h-horizon.md) |
| C. Prévisions historiques externes | Source supplémentaire | Fidèle à l'usage réel | Source non confirmée, licence et coût à étudier |
| D. Sans météo | — | Aucun risque | Perd l'objectif « vols + météo » |

## Décision

**Option A**, approuvée par le propriétaire : les variables météo sont celles de la dernière observation dont l'horodatage est ≤ T-2h pour l'aéroport de départ ; toute observation postérieure est exclue.

**Condition** : l'option A n'est maintenue que si les horodatages météo permettent réellement de reconstruire les observations disponibles à T-2h. Le test de faisabilité est décrit dans [dataset-card.md](../../dataset-card.md), section 4.

## Si la condition n'est pas satisfaite

1. Signaler le **blocage** dans PROGRESS.md et dans cette ADR.
2. **Ne créer aucune donnée artificielle** (pas de météo simulée, pas d'interpolation inventée).
3. Le propriétaire arbitre entre les options C, D ou un autre dataset.
4. Les tâches dépendantes (T3.4, T3.7 partie météo, mode de prédiction D-02 qui utilise la météo) ne démarrent pas.

## Conséquences

- La limite sera affichée : la météo est une observation antérieure, pas une prévision.
- Jointure temporelle « as-of » requise (T3.4), testée (test météo de [testing-strategy.md](../../04-quality/testing-strategy.md)).
- Lié à : T1.5, point go/no-go G1, R-02, R-19.
