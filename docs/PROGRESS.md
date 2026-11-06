# AeroPulse — Avancement (anciennement FlightWise)

> Document vivant : à mettre à jour à la fin de chaque session de travail.
> Les descriptions des étapes sont dans [ROADMAP.md](ROADMAP.md) : ne pas les dupliquer ici.

**Dernière mise à jour :** 2026-11-06
**Étape en cours :** Planification — ADR-0016, D-18 et D-19 **approuvées** ; licences lues ; en attente de votre feu vert pour WP0 et le téléchargement
**Statut :** aucune implémentation ; aucun téléchargement hors échantillon public de 500 lignes ; aucune ressource AWS
**Index de la documentation :** [README.md](README.md)

## Vue d'ensemble

| Étape | Intitulé | Statut |
|---|---|---|
| 1 | Acquérir, explorer et vérifier le dataset | à faire — **bloquée** : approbation de D-18, licences BTS/NOAA à confirmer |
| 2 | Pipeline de préparation | à faire |
| 3 | Variables T-2h et cibles | à faire |
| 4 | Modèles en local | à faire |
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
- Restent en WP0 : T0.6 (AWS Budgets, nécessite un compte AWS), T0.7 (relecture), T0.8 (estimation de coûts, G0)

## Résultats de l'étude (résumé)

- Le téléchargement complet de la table Mostly Right dépasse l'allocation gratuite (100 000 lignes/mois pour 1 056 897 lignes annoncées) ; abonnement exclu.
- **Le cutoff du dataset publié est T-1h** (500/500 lignes), pas T-2h, et il ne contient pas l'historique météo : même acheté, il ne fournirait pas la météo à T-2h.
- BTS fournit tous les champs de vol nécessaires ; NOAA Global Hourly fournit des observations horodatées en UTC pour JFK, LGA et EWR (63 Mo pour 2023–2025).
- Aucune archive de **prévisions** gratuite, complète et officielle n'a été vérifiée : prévisions hors MVP.
- Licences formelles BTS et NOAA Global Hourly : **non vérifiées** (pages inaccessibles).
- Recommandation : **option B**, reconstruction locale à coût nul, échantillon de 500 lignes comme recette.

## Prochaines actions

1. **Votre décision** : accepter (ou non) le risque résiduel de licence BTS (aucun texte de licence lisible, aucune restriction trouvée) pour autoriser le téléchargement complet (T1.1).
2. Code T1.1 prêt à écrire (manifeste de sources + téléchargeur avec mode « dry-run ») : non exécuté tant que le point 1 n'est pas tranché.
3. T0.8 : estimation de coûts (G0) — non bloquée.
4. Révoquer la clé Mostly Right exposée (voir Sécurité).

## Blocages et vérifications en attente

| Sujet | État | Détail |
|---|---|---|
| Stratégie d'acquisition (D-18) et D-19 | **Approuvées le 2026-11-06** | — |
| Licence NOAA Global Hourly | **Lue** : ouverte, attribution demandée | Citer NOAA dans les livrables |
| Licence BTS On-Time | **Aucun texte lu** (pages en 403), aucune restriction trouvée | Acceptation du risque résiduel par le propriétaire (AC-23) |
| Horodatages météo / T-2h (D-01 sous condition) | **En attente de vérification** | Sur les observations NOAA reconstruites (AC-24) |
| Couverture NOAA 2025 jusqu'à fin juillet, noms et tailles réels des archives BTS | À mesurer | T1.1–T1.2 |
| Dates exactes du découpage (D-17) | En attente | T3.6 |
| Modèle Bedrock (D-12c) | **En attente de vérification** | [ADR-0012](05-decisions/adr/0012-bedrock-model-selection.md) |
| Estimation de coûts vs 100 USD/mois | À produire | Bloque tout déploiement payant (G0) |
| Date limite, temps disponible, accès à un compte AWS | Non fournis / non confirmés | Calendrier |
| Environnement Python local | pandas/PyArrow/DuckDB non installés | WP0 (uv) |

## Sécurité

Une clé API Mostly Right (`mr_use_…`) a été collée en clair dans la conversation. Elle n'a pas été utilisée ni écrite dans le dépôt. **Il est recommandé de la révoquer et de la regénérer.**

## Suivi des coûts AWS

Budget cible : 100 USD/mois, alertes AWS Budgets à 50 %, 80 %, 100 % (**à configurer**, T0.6 ; elles ne coupent pas les dépenses). Aucune ressource AWS active, aucun abonnement Mostly Right. Checklist : [cost-estimate.md](04-quality/cost-estimate.md).
