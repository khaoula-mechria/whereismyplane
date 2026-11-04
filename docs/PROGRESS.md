# FlightWise — Avancement

> Document vivant : à mettre à jour à la fin de chaque session de travail.
> Les descriptions des étapes sont dans [ROADMAP.md](ROADMAP.md) : ne pas les dupliquer ici.

**Dernière mise à jour :** 2026-11-04
**Étape en cours :** Étape 1 — Explorer et vérifier le dataset
**Statut :** non démarrée

## Vue d'ensemble

| Étape | Intitulé | Statut |
|---|---|---|
| 1 | Explorer et vérifier le dataset | à faire |
| 2 | Pipeline de préparation | à faire |
| 3 | Variables T-2h et cibles | à faire |
| 4 | Modèles en local | à faire |
| 5 | Entraînement sur SageMaker | à faire |
| 6 | Infrastructure avec CDK | à faire |
| 7 | API et dashboard | à faire |
| 8 | Assistant Bedrock (Tool Calling) | à faire |
| 9 | RAG et monitoring | à faire |

Statuts possibles : à faire, en cours, bloquée, terminée.

## Fait

- [x] 2026-11-04 — Synthèse des décisions rédigée
- [x] 2026-11-04 — Feuille de route et fichier d'avancement créés (à réviser)

## Prochaines actions

1. Réviser `ROADMAP.md` et `PROGRESS.md`.
2. Créer README, `.gitignore`, configuration du projet.
3. Récupérer le dataset Flights & Weather 2022 et vérifier son schéma réel.
4. Commencer `docs/data_dictionary.md`.

## Blocages et questions ouvertes

- Météo à T-2h : prévision ou dernière observation disponible ? À trancher à l'étape 3.
- Gestionnaire de dépendances Python : à choisir (uv, Poetry ou pip).
- Le dataset contient-il bien ~111 000 vols, et uniquement des départs de SEA et PDX ?

## Décisions récentes

Aucune décision nouvelle depuis la synthèse. Les ADR iront dans `docs/decisions/`.

## Suivi des coûts AWS

Aucune ressource AWS active.
