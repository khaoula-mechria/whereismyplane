# AeroPulse — Avancement (anciennement FlightWise)

> Document vivant : à mettre à jour à la fin de chaque session de travail.
> Les descriptions des étapes sont dans [ROADMAP.md](ROADMAP.md) : ne pas les dupliquer ici.

**Dernière mise à jour :** 2026-11-06
**Étape en cours :** Planification — décisions arbitrées, vérifications en attente ; avant WP0 / Étape 1
**Statut :** documentation mise à jour (dataset NYC 2023–2025, budget, région) ; développement non démarré
**Index de la documentation :** [README.md](README.md)

## Vue d'ensemble

| Étape | Intitulé | Statut |
|---|---|---|
| 1 | Explorer et vérifier le dataset | à faire — **bloquée** (source, fichier, licence non fournis) |
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

- [x] 2026-11-04 — Synthèse des décisions rédigée
- [x] 2026-11-04 — Feuille de route et fichier d'avancement créés
- [x] 2026-11-05 — Dossier de planification et de conception rédigé (`docs/01-planning` à `docs/05-decisions`)
- [x] 2026-11-06 — Décisions D-01 à D-17 enregistrées ; projet renommé AeroPulse ; dataset remplacé par NYC Flight Delays and Weather (2023–2025) ; région `us-east-1` et budget 100 USD/mois intégrés ; ADR-0010 à ADR-0015, `dataset-card.md`, `data-dictionary.md` (squelette) et `cost-estimate.md` créés — non commité

## Prochaines actions (non bloquées)

1. T0.1–T0.5 : fondations locales du dépôt (structure, uv, lint, CI, constantes) — aucune ressource AWS.
2. T0.8 : remplir [cost-estimate.md](04-quality/cost-estimate.md) avec les tarifs officiels `us-east-1`, scénarios nominal et pessimiste, puis faire approuver (**G0**).
3. Fournir : source exacte, emplacement du fichier et licence du dataset (débloque WP1).
4. Fournir (si possible) : date limite, temps disponible, confirmation d'un accès à un compte AWS.

## Blocages et vérifications en attente

| Sujet | État | Détail |
|---|---|---|
| Source, emplacement, licence du dataset | **Non fournis** | Bloque T1.1 et WP1–WP2 |
| Caractéristiques annoncées (1 056 897 vols, 33 variables, JFK/EWR/LGA, 2023-01 → 2025-07) | **Non vérifiées** | Inspection T1.2 |
| Horodatages météo / reconstruction à T-2h (D-01 sous condition) | **En attente de vérification** | Si impossible : blocage signalé, aucune donnée artificielle ([ADR-0009](05-decisions/adr/0009-weather-at-t2h.md)) |
| Dates exactes du découpage (D-17) | En attente | Après couverture mensuelle (T3.6) |
| Modèle Bedrock (D-12c) | **En attente de vérification** | [ADR-0012](05-decisions/adr/0012-bedrock-model-selection.md), T8.1 |
| Estimation de coûts vs 100 USD/mois | À produire | Bloque tout déploiement payant (G0) |
| Date limite, temps disponible, taille d'équipe | Non fournis | Calendrier non établi |
| Langue de l'interface | Français proposé | À confirmer en T7.1 |

Détail : [decisions-pending.md](05-decisions/decisions-pending.md).

## Décisions récentes

D-01 à D-17 arbitrées (D-01 et D-17 partiellement conditionnées, D-12c en attente). ADR-0001 à ADR-0015 dans `docs/05-decisions/adr/`.

## Suivi des coûts AWS

Budget cible : 100 USD/mois, alertes AWS Budgets à 50 %, 80 %, 100 % (**à configurer**, T0.6 ; elles ne coupent pas les dépenses). Aucune ressource AWS active, aucun déploiement. Checklist de contrôle : [cost-estimate.md](04-quality/cost-estimate.md).
