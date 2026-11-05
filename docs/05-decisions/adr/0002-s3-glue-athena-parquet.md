# ADR-0002 — S3 + Glue + Athena + Parquet plutôt que Redshift

- **Statut** : Acceptée (synthèse du projet)
- **Date** : 2026-11-05 (formalisation)

## Contexte

Environ 1 056 897 vols annoncés [non vérifié, U-01] sur le dataset NYC 2023–2025 ([ADR-0010](0010-dataset-nyc-2023-2025.md)), requêtes analytiques occasionnelles, budget de 100 USD/mois ([ADR-0011](0011-region-budget-cost-guardrails.md)), pas de serveur à administrer.

## Décision

- Stockage objet **S3** en trois zones (raw, processed, analytics).
- **Glue Data Catalog** pour les schémas ; **Glue/PySpark** pour l'ETL.
- **Athena** pour le SQL, avec un workgroup dédié.
- **Parquet** pour les zones processed et analytics, partitionné modestement par période.

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Redshift | Entrepôt dédié inutile pour ce volume ; coût et administration. À réévaluer si le volume ou la fréquence des requêtes augmentent |
| RDS / PostgreSQL | Pas de besoin transactionnel ; plus à administrer |
| Fichiers locaux seulement | Ne répond pas à l'objectif d'architecture cloud |

## Conséquences

- (+) Coût à la requête, peu d'administration, séparation stockage/calcul.
- (−) Latence d'Athena plus élevée qu'une base dédiée : agrégats pré-calculés pour les routes du dashboard.
- (−) Glue/PySpark reste modeste pour un volume de l'ordre du million de lignes (non vérifié) : transformations écrites et validées d'abord en local ([ADR-0005](0005-local-first-development.md)) ; coût des jobs Glue à estimer ([cost-estimate.md](../../04-quality/cost-estimate.md)).
- Le SQL est écrit dans un dialecte portable entre DuckDB (local) et Athena ; la parité est vérifiée en T6.3.
