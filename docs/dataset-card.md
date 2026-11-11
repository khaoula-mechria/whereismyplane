# Fiche du dataset — NYC Flight Delays and Weather (2023–2025)

> Statut : **spécification de référence ; stratégie d'acquisition proposée dans [ADR-0016](05-decisions/adr/0016-dataset-acquisition-strategy.md), en attente d'approbation.** Étude détaillée : [data-acquisition-study.md](data-acquisition-study.md). Dataset initial (Flights & Weather 2022) abandonné ([ADR-0010](05-decisions/adr/0010-dataset-nyc-2023-2025.md)).

Légende : **[V]** vérifié (source indiquée) · **[H]** hypothèse · **[?]** non résolu · **[NV]** annoncé, non vérifié.

## 1. Identité

| Champ | Valeur | Statut |
|---|---|---|
| Titre publié | « NYC flight delays and weather, 2023–2025 » ; table `nyc_flight_delays_ml` ; slug `nyc-flight-delays-and-weather-januaryjuly-2025` (le slug dit « januaryjuly-2025 », le titre « 2023–2025 ») | [V] catalogue public |
| Éditeur | Mostly Right (`mostlyrightmd`) — https://mostlyright.md/datasets/nyc-flight-delays-and-weather-januaryjuly-2025 | [V] |
| Version publiée | publié le 2026-09-14, mis à jour le 2026-10-01 (catalogue) ; la page affichait aussi « v4 » et une cadence « Daily » alors que le texte dit « monthly BTS exports » | [V] affichage, incohérence [?] |
| Sources d'origine déclarées | BTS On-Time Reporting, NOAA Global Hourly, historique des stations ISD ; OurAirports pour les aéroports | [V] déclaré par l'éditeur |
| Licence de la table | champ `license` du catalogue : **`null`** ; texte : « government-data public-domain assertions » | [V] ; **licence formelle non établie [?]** |
| Accès gratuit | échantillon public de 500 lignes ; au-delà : compte (allocation de 100 000 lignes/mois, partagée) ou abonnement | [V] |
| Téléchargement complet | compte comme lignes lues sur le plan gratuit ; **non retenu** (pas d'abonnement) | [V] / décision du propriétaire |
| Emplacement local du fichier | aucun fichier complet | — |

## 2. Caractéristiques

| Caractéristique | Annoncé (éditeur) | Vérifié par nous | Source de la vérification |
|---|---|---|---|
| Nombre de vols | 1 056 897 (moyenne 34 093 par mois) | **Non** [NV] | — (à reconstruire, AC-23) |
| Colonnes | 33 | **Oui, 33 noms et significations** [V] | catalogue public et échantillon |
| Aéroports d'origine | JFK, EWR, LGA | Oui sur l'échantillon [V] ; ensemble [NV] | échantillon |
| Fenêtre | 2023-01-01 → 2025-07-31 ; dates en heure de New York, horodatages en UTC | Début : oui sur l'échantillon (2023-01-01) [V] ; fin [NV] | échantillon |
| Destinations | domestiques ; internationaux et opérateurs non déclarants exclus | 72 destinations dans l'échantillon [V] | échantillon |
| Appariement météo | 99,96 % des vols ; 384 sans météo ; aucune observation après le cutoff ni de plus de 3 h | Échantillon : 0 sans météo, 0 après cutoff, âge ≤ 59 min [V] ; ensemble [NV] | échantillon |
| `destination_name` manquant | 42 645 vols | 42/500 dans l'échantillon [V] ; ensemble [NV] | échantillon |
| Validation | « All 31 monthly totals match the source exports, with zero duplicate flight keys » | 0 doublon dans l'échantillon [V] ; reste [NV] | échantillon |

## 3. Point critique : cutoff de 1 heure, pas de 2 heures [V]

Le dataset définit `feature_cutoff_utc = scheduled_departure_utc − 60 min` (500/500 lignes) et apparie la dernière observation météo « at or before the one-hour cutoff ». Le contrat d'AeroPulse est **T-2h** ([ADR-0003](05-decisions/adr/0003-t-minus-2h-horizon.md)). Les colonnes météo de ce dataset ne peuvent donc pas servir telles quelles, et l'historique des observations n'y est pas disponible. Voir [data-acquisition-study.md](data-acquisition-study.md) §1.

L'éditeur précise aussi : « Weather observation timestamps do not establish when reports became available » et « Retrospective research, with no guarantee of point-in-time report availability ».

## 4. Échantillon public (500 lignes) — résumé [V]

Un seul jour (2023-01-01), JFK 240 / LGA 162 / EWR 98, 12 compagnies, 72 destinations, aucun doublon de clé, UTC = heure locale + 5 h, retards cohérents avec les indicateurs, 5 annulés (dont un avec un retard renseigné), 1 dérouté, nombres renvoyés en chaînes par l'API anonyme. **Non représentatif, inutilisable pour entraîner ou évaluer.** Détail dans l'étude, §2.

## 5. Sources d'origine

| Source | Fichiers | Licence / conditions |
|---|---|---|
| BTS On-Time Reporting Carrier | 31 archives mensuelles (2023-01 → 2025-07), 900 608 820 octets au total [V : HEAD] ; formulaire de téléchargement et répertoire `PREZIP` | **Aucun texte de licence ou de restriction lu** pour cette table (pages de politique en 403) ; pas de licence formelle établie [?]. Voir étude §3 |
| NOAA NCEI Global Hourly | 9 CSV (3 stations × 2023–2025), 63 137 551 octets [V] ; bucket `noaa-global-hourly-pds` (`us-east-1`) | **Ouverte, usage libre, attribution demandée, sans suggérer l'aval de NOAA, sans présenter des données modifiées comme originales** [V : registre AWS NODD, lu le 2026-11-06]. Restriction WMO Rés. 40 : données **non américaines** seulement |
| Stations | JFK 74486094789 · LGA 72503014732 · EWR 72502014734 | [V] (noms lus dans les fichiers 2024) |

NOAA : conditions lues et acceptables (attribution à citer dans les livrables). BTS : aucune restriction trouvée mais aucune licence formelle non plus ; usage prévu = analyse locale, sans redistribution des fichiers bruts (AC-23 partiellement satisfait, résidu à accepter par le propriétaire). Les fichiers bruts ne sont ni versionnés ni redistribués.

## 6. Test de faisabilité de D-01 (météo disponible à T-2h)

D-01 reste tranchée **sous condition** (option A : dernière observation ≤ T-2h). Éléments d'évidence mis à jour :

| Question | Évidence | Statut |
|---|---|---|
| Observations avec horodatage propre ? | ISD : `DATE` en CSV, heure d'observation « based on UTC » ; ligne de 00:51 avec METAR « 010051Z » | [V] |
| Retrouver, pour un vol, la dernière observation ≤ T-2h à l'aéroport de départ ? | Structure des fichiers NOAA le permet (séries horaires par station) ; à exécuter sur les vraies données | [H] jusqu'à T1.5 |
| Âge acceptable ? | Âge à mesurer sur 2023–2025 ; Mostly Right borne à 3 h pour T-1h | [?] |
| La météo est-elle fournie seulement « au départ » ? | Non pour NOAA (séries) ; oui pour les colonnes du dataset Mostly Right (une valeur par vol) | [V] |

**En cas de blocage** (observations incomplètes, trous excessifs) : signaler dans PROGRESS.md et ADR-0009, **aucune donnée artificielle** ; arbitrage du propriétaire.

## 7. Découpage chronologique (indicatif, D-17)

Entraînement 2023 + partie de 2024 ; validation fin 2024 ; test 2025 (jusqu'à la dernière date réellement présente). Dates exactes en T3.6 d'après la couverture mensuelle réelle. Le jeu de test 2025 couvre au plus janvier–juillet.

## 8. Limites à afficher (provisoires)

- Données historiques 2023–2025, aéroports JFK/EWR/LGA ; pas de conditions actuelles.
- Météo = dernière observation ≤ T-2h, **pas une prévision** (sous réserve de D-01).
- Contributions SHAP = influence sur le modèle, pas causalité.
- Statistiques sur moins de 30 vols non affichées.

Liens : [data-dictionary.md](data-dictionary.md) · [scope-and-constraints.md](01-planning/scope-and-constraints.md) · [decisions-pending.md](05-decisions/decisions-pending.md)
