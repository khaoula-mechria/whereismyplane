# ADR-0016 — Stratégie d'acquisition du dataset

- **Statut** : **Acceptée le 2026-11-06** (approbation du propriétaire) ; téléchargement complet conditionné à la lecture des licences
- **Date** : 2026-11-06
- **Décision liée** : D-18 ([decisions-pending.md](../decisions-pending.md))
- **Complète** : [ADR-0010](0010-dataset-nyc-2023-2025.md), [ADR-0009](0009-weather-at-t2h.md)

## Contexte

Le téléchargement complet de `nyc_flight_delays_ml` (1 056 897 lignes annoncées) dépasse l'allocation gratuite de 100 000 lignes/mois de Mostly Right ; un abonnement est exclu. L'étude [data-acquisition-study.md](../../data-acquisition-study.md) a établi, entre autres :

1. Le cutoff du dataset est **T-1h** (500/500 lignes de l'échantillon), pas T-2h ; son historique météo n'est pas inclus. Même acheté, il ne fournirait pas la météo à T-2h.
2. BTS fournit tous les champs de vol nécessaires (départ programmé, départ réel, retard au départ, annulation, déroutement) en heures locales.
3. NOAA Global Hourly fournit des observations horodatées en UTC pour JFK, LGA et EWR (identifiants et noms vérifiés), 63 Mo pour 2023–2025.
4. Aucune archive de **prévisions** gratuite, complète et officielle n'a été vérifiée pour 2023–2025.
5. Les licences formelles de BTS et de NOAA Global Hourly n'ont **pas** pu être vérifiées (pages inaccessibles).

## Options

| Option | Description | Coût | Atouts | Limites |
|---|---|---|---|---|
| **A. Échantillon seul** | 500 lignes publiques | 0 | Recette du schéma | Un seul jour : ni entraînement ni évaluation |
| **B. Reconstruction depuis BTS + NOAA** | ETL local depuis les sources d'origine, cutoff paramétré à T-2h | 0 (local) | Respecte T-2h, historique météo complet, contrôle total, reproductible, 1 M vols attendus | Effort d'ingénierie ; licences à confirmer ; pas de prévisions |
| C. Abonnement Mostly Right ($49) | Téléchargement complet | 49 USD | Rapide | Refusé ; météo à T-1h seulement ; licence de la table non établie |
| D. 100 000 lignes gratuites | Sous-ensemble via l'API | 0 | Instantané | Quota mensuel entier consommé ; sous-ensemble trop petit ; météo à T-1h |

## Décision (approuvée)

1. **Option B** est la source d'entraînement : reconstruction locale depuis BTS (vols) et NOAA Global Hourly (observations), période 2023-01 → 2025-07, origines JFK/EWR/LGA, cutoff = départ programmé − 2 h, jointure « as-of » observation ≤ cutoff.
2. **Option A** sert de **référence de recette** : test de réplication sur les 500 lignes du 2023-01-01 (avec cutoff paramétré à 1 h pour retrouver les colonnes météo de l'éditeur), puis contrôle de cohérence des schémas.
3. Les **prévisions archivées** sont **hors MVP**. Un spike optionnel (TAF via IEM, HRRR sur AWS) pourra être étudié ensuite ; rien n'est supposé disponible.
4. **D-01 (option A, observation ≤ T-2h)** est maintenue ; AC-24 mesure la faisabilité sur les vraies données.
5. Aucun abonnement, aucune ressource AWS payante : l'acquisition et la transformation sont locales (G0 inchangé).
6. Les fichiers bruts ne sont pas versionnés. Une confirmation de licence est un prérequis avant toute publication de données dérivées.

## Conditions et vérifications préalables à l'implémentation

| Point | Statut |
|---|---|
| Approbation de cette ADR par le propriétaire | **Reçue le 2026-11-06** |
| Licence NOAA ISD/Global Hourly | **Lue** : ouverte, attribution demandée (restriction WMO Rés. 40 : données non américaines) |
| Licence BTS On-Time | **Aucun texte lu** (pages de politique en 403), aucune restriction trouvée ; **risque résiduel à accepter par le propriétaire** avant le téléchargement complet |
| Motif des noms de fichiers BTS, tailles réelles | À mesurer |
| Couverture NOAA 2025 jusqu'à juillet | À vérifier |
| Environnement Python (uv, pandas/PyArrow/DuckDB) | À installer en WP0 |
| Décision D-19 : annulations/déroutages | Tranchée (exclus des cibles ML, conservés en statistiques) |

## Conséquences

- (+) Respect de T-2h, indépendance vis-à-vis d'un fournisseur payant, reproductibilité, coût nul.
- (+) La reconstruction peut être comparée au dataset publié (décomptes mensuels annoncés, échantillon).
- (−) Effort d'ingénierie accru (WP1–WP2 plus chargés), fuseaux/DST à traiter, risque de divergence avec le dataset publié.
- (−) Qualité ISD attribuée a posteriori : fuite faible à documenter.
- Impact : T1.1–T1.6, T2.1–T2.5 ([task-breakdown.md](../../03-project-management/task-breakdown.md)), AC-23, AC-24.

## Si l'option B échoue

Repli, par ordre : (1) réduire la période (moins de mois) tout en restant chronologique ; (2) sous-ensemble Mostly Right de 100 000 lignes **uniquement** pour développer le pipeline, avec horizon T-1h documenté comme écart à ADR-0003 (décision explicite du propriétaire) ; (3) abonnement ponctuel (décision du propriétaire).
