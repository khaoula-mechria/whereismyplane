# Fiche du dataset — NYC Flight Delays and Weather (2023–2025)

> Statut : **candidat principal confirmé par le propriétaire du projet ; aucune caractéristique n'est vérifiée.** Le fichier réel n'a pas encore été inspecté. Les valeurs ci-dessous sont des **annonces**. Voir [ADR-0010](05-decisions/adr/0010-dataset-nyc-2023-2025.md). Le dataset initial (Flights & Weather 2022) est abandonné.

## 1. Identité

| Champ | Valeur | Statut |
|---|---|---|
| Nom | NYC Flight Delays and Weather (2023–2025) | Confirmé (choix) |
| Source exacte (plateforme, URL, auteur, version, date de téléchargement) | À documenter | **En attente** — à fournir par le propriétaire |
| Licence et conditions d'usage | À vérifier | **En attente de vérification** |
| Emplacement local du fichier | À fournir | **En attente** |
| Taille du fichier, format, somme de contrôle | À relever | Non vérifié |

Règle : aucune donnée n'est utilisée dans le dépôt avant que la licence permette cet usage. Le fichier n'est pas versionné dans git (`data/` ignoré).

## 2. Caractéristiques annoncées vs vérifiées

| Caractéristique | Annoncé | Vérifié | Tâche |
|---|---|---|---|
| Nombre de vols | ≈ 1 056 897 | Non | T1.2 |
| Nombre de variables | 33 | Non | T1.2 |
| Aéroports | JFK, EWR, LGA | Non | T1.2 |
| Période | janvier 2023 – juillet 2025 | Non | T1.2 |
| Contenu | Vols historiques + météo associée | Non | T1.2 |
| Horodatage météo | Inconnu | **Non — critique pour D-01** | T1.5 |
| Nature des aéroports (départ seul ? arrivées aussi ?) | Inconnue | Non | T1.2 |
| Vols annulés / déroutés | Inconnu | Non | T1.2 |

## 3. Vérifications à faire à l'inspection (T1.1 à T1.6)

1. Colonnes, types, unités, fuseaux horaires ; comparaison avec les 33 variables annoncées.
2. Couverture temporelle **mois par mois** (trous, mois incomplets, notamment juillet 2025).
3. Volumétrie par aéroport, compagnie, itinéraire (évaluation de IR-01, R-17).
4. Doublons et clé candidate d'un vol.
5. Prévalence des retards > 15 min et distribution de `dep_delay` (déséquilibre, R-04).
6. Traitement des annulations/déroutages (inclus ou exclus de la cible : à décider avec les données).
7. **Météo** : voir section 4.
8. Licence, source, version.

## 4. Test de faisabilité de D-01 (météo disponible à T-2h)

La décision D-01 (option A : dernière observation ≤ T-2h) est **tranchée sous condition** : elle n'est maintenue que si les horodatages météo permettent de reconstruire ce qui était disponible à T-2h.

| Question | Si oui | Si non |
|---|---|---|
| Chaque observation météo a-t-elle un horodatage propre (heure d'observation) ? | Continuer | **Blocage** |
| Peut-on, pour un vol, retrouver la dernière observation dont l'horodatage est ≤ T-2h pour l'aéroport de départ ? | Continuer | **Blocage** |
| L'âge de cette observation est-il acceptable (âge maximal à fixer à l'inspection) pour une part suffisante de vols ? | Option A confirmée | Documenter la limite ; si insuffisant, blocage |
| La météo fournie est-elle seulement « au moment du départ » (une valeur par vol, sans série temporelle) ? | — | **Blocage** pour la météo (c'est une fuite) |

**En cas de blocage** : le signaler dans [PROGRESS.md](PROGRESS.md) et dans une mise à jour de [ADR-0009](05-decisions/adr/0009-weather-at-t2h.md), **sans créer de données artificielles** (pas d'interpolation inventée, pas de météo simulée). Les alternatives à arbitrer alors par le propriétaire : source de météo historique externe (à documenter et licencier), entraînement sans variables météo, ou autre dataset.

Les tâches T3.4 (jointure météo) et T3.7 (non-fuite météo) ne démarrent pas avant la levée de cette condition.

## 5. Découpage chronologique (indicatif, D-17)

Principe tranché : séparation chronologique adaptée à la période réellement disponible.

| Jeu | Période indicative | Remarque |
|---|---|---|
| Entraînement | 2023 et une partie de 2024 | Fin exacte à fixer après inspection |
| Validation | période ultérieure de 2024 | Début/fin exacts à fixer |
| Test | 2025 (jusqu'à la dernière date réellement présente) | Peut être incomplet si juillet 2025 est partiel |

Les dates exactes sont déterminées en T3.6, une fois la couverture mensuelle vérifiée. Elles ne sont pas figées ici. Une répartition en proportion de vols (et non seulement en mois) sera examinée pour éviter un jeu de validation ou de test trop petit.

## 6. Limites à afficher (provisoires)

- Les données sont historiques (2023–2025) et limitées à JFK, EWR et LGA (sous réserve de vérification) ; pas de conditions actuelles.
- La météo utilisée est une observation antérieure à T-2h, pas une prévision (sous réserve de D-01).
- Les contributions SHAP indiquent une influence sur le modèle, pas une cause.

Liens : [data-dictionary.md](data-dictionary.md) · [scope-and-constraints.md](01-planning/scope-and-constraints.md) · [decisions-pending.md](05-decisions/decisions-pending.md)
