# AeroPulse — Avancement (anciennement FlightWise)

> Document vivant : à mettre à jour à la fin de chaque session de travail.
> Les descriptions des étapes sont dans [ROADMAP.md](ROADMAP.md) : ne pas les dupliquer ici.

**Dernière mise à jour :** 2026-11-13
**Étape en cours :** Étapes 1–2 largement faites en local (données acquises, météo T-2h, pipeline de préparation) ; WP2 et WP3 terminés en local ; prochaine tâche : WP4 (baselines puis modèles)
**Statut :** Parquet Mostly Right (27 Mo) et NOAA (9 CSV, 63 Mo) téléchargés en local (`data/`, non versionné) ; BTS non téléchargé (optionnel) ; aucune ressource AWS
**Index de la documentation :** [README.md](README.md)

## Vue d'ensemble

| Étape | Intitulé | Statut |
|---|---|---|
| 1 | Acquérir, explorer et vérifier le dataset | **en cours** — données téléchargées et profilées ; reste la vérification de licence de la table Mostly Right |
| 2 | Pipeline de préparation | **terminée en local** (T2.2–T2.8) ; T2.1 BTS non applicable (source = Parquet) |
| 3 | Variables T-2h et cibles | **terminée en local** (T3.1–T3.8) ; revue de non-fuite avant G2 |
| 4 | Modèles en local | **terminée en local** (T4.1–T4.9 ; T4.3 reportée, ADR-0017) ; G3 : go pour la classification |
| 5 | Entraînement sur SageMaker | à faire — conditionnée à G0 (coûts) |
| 6 | Infrastructure avec CDK | à faire |
| 7 | API et dashboard | à faire |
| 8 | Assistant Bedrock (Tool Calling) | à faire — modèle Bedrock à vérifier |
| 9 | RAG et monitoring | à faire |

Statuts possibles : à faire, en cours, bloquée, terminée.

## Fait

- [x] 2026-11-04 — Synthèse des décisions rédigée ; feuille de route et fichier d'avancement créés
- [x] 2026-11-05 — Dossier de planification et de conception rédigé
- [x] 2026-11-06 — Décisions D-01 à D-17 enregistrées ; AeroPulse ; dataset NYC 2023–2025 ; `us-east-1` ; budget 100 USD/mois ; ADR-0010 à 0015
- [x] 2026-11-06 — Étude de faisabilité de l'acquisition : [data-acquisition-study.md](data-acquisition-study.md), [dataset-card.md](dataset-card.md) et [data-dictionary.md](data-dictionary.md) mis à jour, [ADR-0016](05-decisions/adr/0016-dataset-acquisition-strategy.md) proposée — non commité

- [x] 2026-11-06 — **WP0 (local) : T0.1–T0.5 réalisées** — structure du dépôt, `pyproject.toml` (uv), `.gitignore`, `.env.example`, `src/aeropulse/config.py` (seuil 15 min, horizon T-2h, colonnes interdites, stations NOAA, seuil de 30 vols), lint (ruff), typage strict (mypy), 8 tests (pytest), scan de secrets, pre-commit, CI GitHub Actions. Toutes les vérifications locales passent ; la CI n'a pas encore tourné sur GitHub — non commité
- [x] 2026-11-06 — **T1.1 (code, dry-run)** : `aeropulse.data.manifest` / `aeropulse.data.download` (manifeste, résolution par HEAD, téléchargement atomique avec somme de contrôle, désactivé sans `--execute` ; BTS exige en plus `--accept-bts-licence-risk`). Dry-run réel : **40/40 fichiers résolus** (31 BTS + 9 NOAA), 963 746 371 octets au total, **aucun téléchargement**. Motif des noms BTS établi (sans parenthèses). 15 tests passent
- [x] 2026-11-14 — **T4.9 + D-22 approuvée** (réponse « oui » du propriétaire à la question G3/D-22) : `models/quality.py` (contrôle D-22, seuils dans `config.py`, testé sur les valeurs mesurées et des valeurs dégradées), `models/release.py` (export du classifieur, `manifest.json`, version `clf-f25ebbd328c5`, sans régresseur), `models/predict.py` (prédicteur partagé, parité exacte avec l'entraînement sur 20 000 vols réels, explications ≥ 3 contributions). Empreinte identique à celle du modèle évalué sur le test. **WP4 terminé en local.** 55 tests, ruff, mypy strict OK — non commité
- [x] 2026-11-14 — **T4.8 (verdict G3 : go classification ; D-22 approuvée)** : synthèse G3 et cibles de qualité dans [model-report.md](04-quality/model-report.md) §10 ; **D-22 proposée** (gain de PR-AUC ≥ +0,05 sur la baseline, ROC-AUC ≥ 0,65, calibration ≤ 0,03, tests de non-fuite verts) ; verdict G3 proposé : **go pour la classification** (+0,106 de PR-AUC sur le test, hors intervalle de confiance), avec la réserve que l'indicateur reste modeste (≈ 2 alertes sur 3 fausses). Seuils codés après approbation — non commité
- [x] 2026-11-14 — **D-21 / ADR-0017 : régression reportée, pas abandonnée (décision du propriétaire : « pour le moment, mais peut-être ajoutée »)** : classification seule pour l'instant, un seul endpoint SageMaker, `/predict` sans durée estimée, AC-06 suspendu, T4.3 reportée ; conditions de réouverture dans l'ADR. Documentation alignée (exigences FR-06/08/09/13/14, critères, cas d'usage, API, architecture, diagrammes, jalons, tâches, dictionnaire, ROADMAP, ADR-0007 modifiée, index des ADR, registre des décisions) ; estimation de coûts recalculée pour un endpoint (nominal 6,61 USD avec Haiku, pessimiste 60,26 USD, un endpoint oublié un mois 83,95 USD). Le code de régression reste comme trace de recherche, sans livrable — non commité
- [x] 2026-11-14 — **T4.6 évaluation finale sur le test (usage unique, exécutée sur « go test » explicite)** : 200 417 vols, modèles et seuil 0,200 figés avant (empreintes SHA-256 consignées, verrou anti-réexécution). **Classification : PR-AUC 0,415** (IC 95 % 0,410–0,420) contre 0,309 pour la baseline → AC-05 satisfait ; F1 0,447, précision 0,324, rappel 0,719 (≈ 2 alertes sur 3 fausses) ; calibration +1,2 point. **Régression : MAE 22,06 min contre 22,17** pour la meilleure baseline → AC-06 satisfait à la lettre mais de justesse (−0,5 %, dans l'intervalle de confiance) ; RMSE −4 % ; erreur absolue médiane pire (7,1 contre 5,0). Détail et segments : [model-report.md](04-quality/model-report.md) §8. Le test ne doit plus servir. 53 tests, ruff, mypy strict OK — non commité
- [x] 2026-11-14 — **T0.8 (estimation faite, G0 en attente d'approbation)** : [cost-estimate.md](04-quality/cost-estimate.md) rempli à partir des tarifs officiels `us-east-1` (AWS Price List, lus le 2026-11-14, sans offre gratuite) et d'hypothèses d'usage à valider. Chiffres initiaux (deux endpoints), **recalculés après D-21 pour un endpoint** : nominal **6,61 USD** (Haiku) / 17,58 (Sonnet) ; pessimiste (endpoint oublié 1 semaine) **60,26 USD** avec Haiku, **374 USD** avec Sonnet ; un endpoint permanent ≈ 84 USD/mois. Non relevés : CloudFront, Knowledge Bases, durées minimales Glue. Aucune ressource AWS créée — non commité
- [x] 2026-11-14 — **T4.7 SHAP** (`models/explain.py`, contributions exactes de XGBoost sur un échantillon de validation, test non lu ; additivité vérifiée, ≥ 3 contributions locales avec la mention « influence, pas cause » — AC-08 côté fonction) : variables dominantes = heure de départ, taux de retard 28 j aéroport × heure, compagnie, mois ; météo ≈ 27 % de l'importance, historique ≈ 25 %. 52 tests, ruff, mypy strict OK — non commité
- [x] 2026-11-14 — **T4.5 modèles figés, seuil, calibration** (`models/final.py` ; artefacts dans `data/ml/models/`, non versionnés ; test non lu — vérifié par test) : seuil F1 = **0,200** choisi sur la validation (F1 0,429, précision 0,346, rappel 0,566, PR-AUC 0,390, Brier 0,138) ; régression MAE 18,82 min. Calibration : exacte sur l'entraînement, sous-estimation de 1,2 point sur la validation (dérive temporelle, pas un défaut de code). ROADMAP étape 1 alignée sur la source réelle. 51 tests, ruff, mypy strict OK — non commité
- [x] 2026-11-14 — **T4.4 réglage** (`models/tune.py`, recherche aléatoire de 12 essais par tâche sur la validation, test non lu — vérifié par test ; paramètres dans `models/tuned_params.json`) : classification PR-AUC 0,382 → **0,390**, régression MAE 18,833 → **18,821** ; gain du même ordre que la dispersion entre essais, arbres de profondeur 4 meilleurs, `scale_pos_weight` n'aide pas. 50 tests, ruff, mypy strict OK — non commité
- [x] 2026-11-14 — **T4.2–T4.3 premiers modèles** (`models/train.py`, xgboost ajouté ; hyperparamètres de départ non réglés ; validation seulement, test non lu — vérifié par test) : classification, PR-AUC logistique 0,376 / forêt 0,386 / XGBoost 0,382 (baseline 0,279), meilleur F1 0,426 (XGBoost) ; régression, **seul XGBoost à erreur absolue bat la baseline en MAE** (18,83 contre 19,31 min), les pertes quadratiques donnent une MAE pire que la médiane globale. Détail et limites : [model-report.md](04-quality/model-report.md). 49 tests, ruff, mypy strict OK — non commité
- [x] 2026-11-14 — **T4.1 baselines** (`models/baselines.py`, `models/evaluate.py`, scikit-learn ajouté ; ajustées sur l'entraînement, évaluées sur la validation, test jamais lu — vérifié par un test) : classification, référence PR-AUC **0,279** (prévalence 0,191 ; F1 0,374) ; régression, référence MAE **19,31 min** (médiane par aéroport × heure). Détail : [model-report.md](04-quality/model-report.md). 47 tests, ruff, mypy strict OK — non commité
- [x] 2026-11-14 — **WP3 (local) : T3.1–T3.8** — D-17 (dates du découpage) et D-20 (âge max. de la météo : 3 h) **approuvées** ; `config.py` : dates, `MAX_WEATHER_AGE`, contrat de variables (`FEATURE_COLUMNS`, vérifié contre les colonnes interdites). Modules `features/` : `targets`, `split` (test protégé par `final_evaluation=True`), `temporal`, `weather`, `history` (taux de retard 28 j sur les **jours précédents** seulement, NaN sous 30 vols), `build` → `data/ml/ml_dataset.parquet` (1 027 586 lignes : 621 512 / 205 657 / 200 417). `tests/test_leakage.py` (passé strict, futur modifié sans effet sur le passé, météo > T-2h refusée, garde du test). **Défaut corrigé** : relancer le pipeline cumulait les fichiers partitionnés (lignes doublées) ; maintenant idempotent, avec test. 43 tests, ruff, mypy strict OK — non commité. **G2 (non-fuite) : preuves automatisées en place, à confirmer par revue (T0.7)**
- [x] 2026-11-13 — **T2.8 — WP2 terminé en local** : commande unique `uv run python -m aeropulse.data.pipeline --expected-rows 1056897` (validation, préparation, Parquet partitionné, agrégats) ; exécution réelle en ~10 s ; `tests/test_pipeline.py` (bout en bout + blocage si le nombre de lignes diffère, rien d'écrit). 34 tests passent, ruff, mypy strict et scan de secrets OK — non commité
- [x] 2026-11-13 — **T2.6–T2.7 (local)** — `aeropulse.analytics` (seul module avec du SQL) : `queries.py` (dimensions et filtres en listes blanches, valeurs liées par `?`, limite plafonnée à 100, valeurs de carrier/destination issues des données) et `engine.py` (DuckDB en lecture seule sur `data/processed/flights`) ; sortie avec `source`, `period`, `n_flights`, `n_scored` ; **< 30 vols → « données insuffisantes »** (AC-13) ; filtres hors liste, injection, limites refusés (AC-15, tests). `export_aggregates` écrit `data/analytics/{carrier,airport,route}.parquet` (14 compagnies, 3 aéroports, 268 itinéraires). Vérifié sur les vraies données : totaux par aéroport = profil du fichier brut (LGA 403 973, EWR 335 855, JFK 317 069). 32 tests passent — non commité
- [x] 2026-11-13 — **WP2 (local) : T2.2–T2.5** — `aeropulse.data.validate` (contrôles bloquants), `clean` (cible `> 15` recalculée, annulés/déroutés exclus du ML via `ml_eligible` — D-19, météo du fichier T-1h écartée, météo NOAA ≤ T-2h), `pipeline` (CLI → `data/processed/flights/year=/month=`, 28 Mo, non versionné). Exécution réelle : 1 056 897 lignes, 1 027 586 éligibles ML, 208 464 retardés (> 15), recoupés indépendamment avec le fichier brut ; 5 824 vols à exactement 15 min correctement non retardés ; taux de retard 20,9 % (2023), 19,2 % (2024), 21,3 % (2025). 25 vols AA ont un retard réel de 24 à 43 h (conservés ; borne de validation à 7 jours). 26 tests passent — non commité
- [x] 2026-11-13 — **T1.5 (code)** : `aeropulse.data.weather` (lecture NOAA par nom de colonne, décodage ISD, jointure as-of ≤ T-2h, garde-fou anti-fuite, seuil d'âge paramétrable) + `tests/test_weather.py` ; `pandas-stubs` ajouté ; ruff, mypy strict et 21 tests passent. Vérifié sur les vraies données : 1 027 586 vols appariés, 0 fuite, âge médian 24 min, 398 vols > 3 h. Un premier test DuckDB en fuseau local avait légèrement faussé les âges (corrigé) — non commité
- [x] 2026-11-13 — **Données acquises** : Parquet Mostly Right (compte Pro du propriétaire) profilé (1 056 897 lignes, 2023-01-01 → 2025-07-31, 31 mois, 0 doublon, cutoff exactement T-1h) ; NOAA téléchargé (9 CSV). **Test AC-24 réussi** : jointure as-of à T-2h, 100 % des 1 027 586 vols non annulés/déroutés appariés, 0 observation postérieure, âge médian 24 min, 398 vols > 3 h. Docs mis à jour (dataset-card, D-01, D-18, ADR-0016 amendé) — non commité
- Restent en WP0 : T0.6 (AWS Budgets, nécessite un compte AWS), T0.7 (relecture) ; T0.8 faite, approbation G0 en attente

## Résultats de l'étude (résumé)

- Le téléchargement complet de la table Mostly Right dépasse l'allocation gratuite (100 000 lignes/mois pour 1 056 897 lignes annoncées) ; abonnement exclu.
- **Le cutoff du dataset publié est T-1h** (500/500 lignes), pas T-2h, et il ne contient pas l'historique météo : même acheté, il ne fournirait pas la météo à T-2h.
- BTS fournit tous les champs de vol nécessaires ; NOAA Global Hourly fournit des observations horodatées en UTC pour JFK, LGA et EWR (63 Mo pour 2023–2025).
- Aucune archive de **prévisions** gratuite, complète et officielle n'a été vérifiée : prévisions hors MVP.
- Licences formelles BTS et NOAA Global Hourly : **non vérifiées** (pages inaccessibles).
- Recommandation : **option B**, reconstruction locale à coût nul, échantillon de 500 lignes comme recette.

## Prochaines actions

1. **G0 : approuver (ou amender) l'estimation de coûts** recalculée (un endpoint) et ses 4 conditions ; compléter les postes non relevés (CloudFront, Knowledge Bases). **Bloque tout WP5 et tout déploiement AWS payant.** T0.6 (AWS Budgets) nécessite un compte AWS.
2. **Avant G0, en local** : service de prédiction pour un vol saisi (météo ≤ T-2h par jointure as-of et historique, réutilisant `features/` et `Predictor`), préparation de T5.1/T5.2 (scripts d'entraînement et d'inférence testés en local, sans AWS).
3. Relecture de non-fuite avant G2 (T0.7) ; confirmer les conditions d'usage de la table Mostly Right (`license` null). Révoquer la clé Mostly Right exposée (voir Sécurité).

## Blocages et vérifications en attente

| Sujet | État | Détail |
|---|---|---|
| Stratégie d'acquisition (D-18) et D-19 | **Approuvées le 2026-11-06** | — |
| Licence NOAA Global Hourly | **Lue** : ouverte, attribution demandée | Citer NOAA dans les livrables |
| Licence BTS On-Time | Sans objet tant que BTS n'est pas téléchargé (optionnel) | — |
| Licence de la table Mostly Right | `license` = null ; usage local, pas de redistribution | À confirmer auprès de l'éditeur |
| Horodatages météo / T-2h (D-01) | **Vérifié le 2026-11-13** | Seuil d'âge maximal à décider |
| Couverture NOAA 2025 | **Vérifiée** (jusqu'à fin août 2025) | — |
| Dates exactes du découpage (D-17) | **Approuvées le 2026-11-14** | — |
| Modèle Bedrock (D-12c) | **En attente de vérification** | [ADR-0012](05-decisions/adr/0012-bedrock-model-selection.md) |
| Estimation de coûts vs 100 USD/mois | **Produite le 2026-11-14, non approuvée** | Bloque tout déploiement payant tant que G0 n'est pas approuvée ; CloudFront, Knowledge Bases non relevés |
| Date limite, temps disponible, accès à un compte AWS | Non fournis / non confirmés | Calendrier |
| Environnement Python local | Installé (`uv sync`) | — |

## Sécurité

Une clé API Mostly Right (`mr_use_…`) a été collée en clair dans la conversation. Elle n'a pas été utilisée ni écrite dans le dépôt. **Il est recommandé de la révoquer et de la regénérer.**

## Suivi des coûts AWS

Budget cible : 100 USD/mois, alertes AWS Budgets à 50 %, 80 %, 100 % (**à configurer**, T0.6 ; elles ne coupent pas les dépenses). Aucune ressource AWS active, aucun abonnement Mostly Right. Checklist : [cost-estimate.md](04-quality/cost-estimate.md).
