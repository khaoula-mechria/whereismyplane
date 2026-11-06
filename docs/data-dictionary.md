# Dictionnaire de données

> Statut : **dictionnaire de référence du schéma Mostly Right (33 colonnes, vérifié via le catalogue public et l'échantillon de 500 lignes) + correspondance avec les champs BTS/NOAA.** Le dictionnaire du dataset **reconstruit** sera finalisé en T1.3 après construction (ADR-0016). Les statistiques de valeurs manquantes ci-dessous portent sur l'échantillon d'un seul jour (2023-01-01), pas sur l'ensemble.

Légende **Disponible à T-2h** : **oui** (connu à T-2h) · **non** (connu après : résultat, interdit comme variable) · **recalculer** (la colonne existe mais est calculée avec un cutoff de T-1h dans le dataset ; à reconstruire à T-2h). Sources : catalogue public https://mostlyright.md/api/v2/public/datasets/nyc-flight-delays-and-weather-januaryjuly-2025, échantillon public, pages BTS, fichiers NOAA. Types = « logical_type » du catalogue ; l'API anonyme renvoie la plupart des nombres sous forme de chaînes.

## 1. Colonnes (schéma Mostly Right)

| # | Colonne | Type | Signification (catalogue) | Source d'origine | Manquants (échantillon) | Disponible à T-2h | Rôle |
|---|---|---|---|---|---|---|---|
| 1 | `flight_date` | date | Date locale du départ programmé | BTS `FlightDate` | 0 | oui | clé |
| 2 | `carrier` | chaîne | Code compagnie (opérateur déclarant) | BTS `Reporting_Airline` | 0 | oui | variable / clé |
| 3 | `flight_number` | chaîne | Numéro de vol de la compagnie déclarante | BTS `Flight_Number_Reporting_Airline` | 0 | oui | clé (cardinalité élevée, pas une variable brute) |
| 4 | `origin` | chaîne | Aéroport de départ : JFK, EWR ou LGA | BTS `Origin` | 0 | oui | variable / clé |
| 5 | `destination` | chaîne | Aéroport de destination (domestique) | BTS `Dest` | 0 | oui | variable / clé |
| 6 | `scheduled_departure_hhmm` | chaîne | Heure locale programmée HHMM (zéros à gauche) | BTS `CRSDepTime` | 0 | oui | variable dérivée |
| 7 | `departure_hour` | entier | Heure locale programmée | dérivé de `CRSDepTime` | 0 | oui | variable |
| 8 | `month` | entier | Mois civil | dérivé de `FlightDate` | 0 | oui | variable |
| 9 | `day_of_week` | entier | Lundi 1 … dimanche 7 | dérivé de `FlightDate` | 0 | oui | variable |
| 10 | `scheduled_elapsed_minutes` | décimal | Durée de vol programmée (minutes) | BTS `CRSElapsedTime` | 0 | oui | variable |
| 11 | `distance_miles` | décimal | Distance sans escale (miles) | BTS `Distance` | 0 | oui | variable |
| 12 | `departure_delay_minutes` | décimal | Retard au départ observé, signé (négatif = en avance) | BTS `DepDelay` | 4 (annulés) | **non** | **cible de régression** ; base de `is_delayed` |
| 13 | `arrival_delay_minutes` | décimal | Retard à l'arrivée observé, signé | BTS `ArrDelay` | 6 | **non** | interdit |
| 14 | `departure_delayed_15` | booléen | Départ avec ≥ 15 min de retard | BTS `DepDel15` | 4 | **non** | non utilisé : cible recalculée (`> 15`) |
| 15 | `arrival_delayed_15` | booléen | Arrivée avec ≥ 15 min de retard | BTS `ArrDel15` | 6 | **non** | interdit |
| 16 | `cancelled` | booléen | Vol annulé | BTS `Cancelled` | 0 | **non** | interdit en variable ; filtre/décision D-19 |
| 17 | `diverted` | booléen | Vol dérouté | BTS `Diverted` | 0 | **non** | interdit en variable ; filtre/décision D-19 |
| 18 | `scheduled_departure_utc` | horodatage UTC | Départ programmé converti depuis l'heure de New York ; heures ambiguës laissées `null` | BTS + fuseau | 0 | oui | variable dérivée / clé temporelle |
| 19 | `feature_cutoff_utc` | horodatage UTC | **Départ programmé − 1 h** dans ce dataset | dérivé | 0 | **recalculer** (AeroPulse : −2 h) | pivot de la jointure météo |
| 20 | `origin_name` | chaîne | Nom de l'aéroport de départ | OurAirports (déclaré) | 0 | oui | descriptif |
| 21 | `origin_latitude` | décimal | Latitude de l'origine | OurAirports (déclaré) | 0 | oui | descriptif |
| 22 | `origin_longitude` | décimal | Longitude de l'origine | OurAirports (déclaré) | 0 | oui | descriptif |
| 23 | `destination_name` | chaîne | Nom de la destination | OurAirports (déclaré) | 42 | oui | descriptif (manquant sur ≈ 4 % des vols selon l'éditeur) |
| 24 | `destination_latitude` | décimal | Latitude de la destination | idem | 42 | oui | variable possible (distance/direction) |
| 25 | `destination_longitude` | décimal | Longitude de la destination | idem | 42 | oui | idem |
| 26 | `weather_station` | chaîne | Identifiant NOAA USAF+WBAN de la station | ISD | 0 | oui | clé météo |
| 27 | `weather_observed_utc` | horodatage UTC | Dernière observation « routine » ≤ cutoff, au plus 3 h | ISD `DATE` | 0 | **recalculer** (≤ T-2h) | variable dérivée |
| 28 | `weather_age_minutes` | décimal | Âge de l'observation au cutoff | dérivé | 0 | **recalculer** | variable |
| 29 | `temperature_c` | décimal | Température de l'air (°C), qualité acceptée | ISD `TMP` (facteur 10) | 0 | **recalculer** | variable météo |
| 30 | `dewpoint_c` | décimal | Point de rosée (°C) | ISD `DEW` | 0 | **recalculer** | variable météo |
| 31 | `wind_speed_mps` | décimal | Vitesse du vent (m/s) | ISD `WND` | 0 | **recalculer** | variable météo |
| 32 | `visibility_m` | décimal | Visibilité (m) | ISD `VIS` | 0 | **recalculer** | variable météo |
| 33 | `ceiling_m` | décimal | Plafond nuageux (m) | ISD `CIG` | 0 | **recalculer** | variable météo |

Remarque : « quality-accepted » côté éditeur signifie que des codes qualité NOAA ont été appliqués ; ces codes sont attribués après coup (voir [data-acquisition-study.md](data-acquisition-study.md) §4).

## 2. Correspondance avec les sources d'origine

### BTS (table « Reporting Carrier On-Time Performance (1987-present) ») [V]

`FlightDate`, `Reporting_Airline`, `Flight_Number_Reporting_Airline`, `Tail_Number`, `Origin`, `Dest`, `CRSDepTime` (heure locale hhmm), `DepTime`, `DepDelay` (signé), `DepDelayMinutes` (avance → 0), `DepDel15` (≥ 15), `DepartureDelayGroups`, `TaxiOut`, `WheelsOff`, `CRSArrTime`, `ArrTime`, `ArrDelay`, `Cancelled`, `CancellationCode`, `Diverted`, `CRSElapsedTime`, `Distance`, `CarrierDelay`, `WeatherDelay`, `NASDelay`, `SecurityDelay`, `LateAircraftDelay`.

Disponibles à T-2h : `FlightDate`, `Reporting_Airline`, `Flight_Number_Reporting_Airline`, `Origin`, `Dest`, `CRSDepTime`, `CRSElapsedTime`, `Distance`, et `Tail_Number` (pour des variables d'enchaînement, uniquement avec des vols dont le départ précède T-2h). **Tous les autres sont interdits** (départ réel, retards, annulation, déroutement, taxi, wheels-off, arrivée, causes de retard).

### NOAA Global Hourly (en-tête du CSV JFK 2024) [V]

`STATION, DATE, SOURCE, LATITUDE, LONGITUDE, ELEVATION, NAME, REPORT_TYPE, CALL_SIGN, QUALITY_CONTROL, WND, CIG, VIS, TMP, DEW, SLP, AA1…` (environ 100 colonnes).

| Champ | Encodage vérifié (document de format ISD) |
|---|---|
| `DATE` | heure d'observation en UTC |
| `REPORT_TYPE` | `FM-15` METAR (routine), `FM-16` SPECI (spécial), `FM-12` SYNOP ; `SOD`, `SOM` observés dans les données |
| `TMP` | °C, facteur 10, `+9999` = manquant, code qualité associé |
| `WND` | vitesse avec facteur 10, `9999` = manquant (direction, type, codes qualité) |
| `CIG` | plafond en mètres, `99999` = manquant |
| `VIS`, `DEW`, `SLP`, `AA1` | existent ; sentinelles et facteurs à relire dans le document avant l'implémentation |

Codes qualité : `1` = a passé tous les contrôles ; `5` = idem, source NCEI (document de format). La liste complète est à relire en T2.x.

## 3. Variables supplémentaires envisagées (à valider)

Pression (`SLP`), précipitations (`AA1…`), type de rapport, variables d'enchaînement par numéro d'avion, statistiques historiques par aéroport/compagnie/heure (strictement avant T-2h). Aucune n'est décidée.

## 4. Critères

- AC-01 : 100 % des colonnes du dataset **reconstruit** décrites (T1.3).
- AC-03 : aucune colonne « non » ou « interdit » dans les variables.
- AC-24 : faisabilité de la météo à T-2h établie sur les observations NOAA.

Tables dérivées (`flights_clean`, `weather_obs`, `ml_dataset`, agrégats) : [database-design.md](02-architecture/database-design.md).
