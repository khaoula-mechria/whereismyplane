# Conception des données

Le projet n'a pas de base de données transactionnelle en MVP [Proposé] : le « modèle de données » est celui du **lac S3**, décrit dans Glue et interrogé par Athena. Dataset : NYC Flight Delays and Weather 2023–2025 (≈ 1 056 897 vols et 33 variables **annoncés, non vérifiés**, [dataset-card.md](../dataset-card.md)). Les colonnes ci-dessous sont **indicatives** : le schéma réel sera confirmé à l'étape 1 (U-01) et formalisé dans [data-dictionary.md](../data-dictionary.md). En particulier, l'existence d'une table météo séparée avec horodatages (`weather_obs`) n'est pas établie ; si la météo n'est fournie qu'en colonnes du fichier de vols, la structure sera adaptée (voir [ADR-0009](../05-decisions/adr/0009-weather-at-t2h.md)). Diagramme : [er-diagram.md](diagrams/er-diagram.md).

## 1. Zones S3

| Zone | Contenu | Format | Écriture | Lecture |
|---|---|---|---|---|
| `raw/` | Fichiers originaux, jamais modifiés | Format source (CSV probable) | Ingestion | Nettoyage |
| `processed/` | Vols et météo nettoyés | Parquet | Nettoyage | Variables, agrégation |
| `analytics/` | Agrégats et jeu ML | Parquet | Agrégation, variables | Athena, entraînement |
| `models/` | Artefacts de modèles | Selon SageMaker | Pipeline | Endpoints |
| `docs/` | Documents du RAG | Markdown/PDF | Mainteneur | Knowledge Base |
| `athena-results/` | Résultats de requêtes | CSV | Athena | Lambda (temporaire, cycle de vie court) |

Buckets séparés par rôle (données, artefacts, frontend, résultats Athena) pour appliquer des politiques d'accès différentes. Chiffrement activé, accès public bloqué, règles de cycle de vie sur `athena-results/`.

## 2. Tables logiques

| Table | Granularité | Clés | Contenu principal |
|---|---|---|---|
| `flights_clean` | 1 vol programmé | `flight_id` (à définir : compagnie + numéro + date + origine) | compagnie, origine, destination, distance, heure programmée, horaires réels, `dep_delay` |
| `weather_obs` | 1 observation par aéroport et heure | (`airport`, `obs_time`) | température, vent, visibilité, précipitations, etc. (liste réelle à confirmer) |
| `airports` | 1 aéroport | `airport_code` | code, nom, ville, fuseau horaire |
| `airlines` | 1 compagnie | `airline_code` | code, nom |
| `ml_dataset` | 1 vol, vu à T-2h | `flight_id` | variables disponibles à T-2h, `is_delayed`, `dep_delay`, `split` (train/val/test) |
| `agg_airline_delay` | compagnie × période | (`airline_code`, `period`) | nb vols, taux de retard, retard moyen/médian |
| `agg_airport_delay` | aéroport × période | (`airport_code`, `period`) | idem |
| `agg_route_delay` | itinéraire × période | (`origin`, `destination`, `period`) | idem |

Toute table agrégée contient `n_flights` pour appliquer le seuil minimal de 30 vols (IR-01, D-16).

## 3. Règles

- **Fuseaux horaires** : heures stockées en UTC avec le fuseau de l'aéroport conservé ; T-2h calculé sur l'heure programmée [Hypothèse : à confirmer selon les données].
- **Partitionnement** : par mois (`year`, `month`) pour `flights_clean` (une trentaine de partitions environ si la couverture annoncée se confirme) ; l'intérêt est réel surtout pour les filtres par période. Pas de sur-partitionnement : le volume reste modeste. Le choix définitif dépend de la volumétrie réelle (T1.2) et du coût Athena ([cost-estimate.md](../04-quality/cost-estimate.md)).
- **Colonnes interdites pour le ML** : maintenues dans un fichier de configuration unique ; la table `ml_dataset` ne les contient pas (voir [ADR-0003](../05-decisions/adr/0003-t-minus-2h-horizon.md)).
- **Immuabilité** : raw est en écriture unique ; processed et analytics sont reconstructibles depuis raw.
- **Qualité** : contrôles bloquants entre raw → processed (schéma, plages, doublons, dates).
- **Versionnement** : chaque exécution de pipeline écrit dans un préfixe daté ou versionné ; le jeu utilisé par un modèle est identifiable.

## 4. Sorties optionnelles

| Besoin | Option | Statut |
|---|---|---|
| Historique des prédictions | Table DynamoDB ou fichiers S3 | **Écarté en MVP** (D-09 tranchée) |
| Métadonnées de modèles | SageMaker Model Registry | Retenu [Confirmé] |
| Évaluation de l'assistant | Fichiers versionnés dans le dépôt | Proposé |

## 5. Accès

| Consommateur | Accès | Restrictions |
|---|---|---|
| Lambda « analyse » | Athena, lecture sur `processed/` et `analytics/` | Workgroup dédié, limite de volume analysé, rôle lecture seule |
| Pipeline Glue | Lecture raw, écriture processed/analytics | Rôle dédié |
| SageMaker | Lecture `analytics/` (jeu ML), écriture `models/` | Rôle d'exécution dédié |
| Frontend | Aucun accès direct aux données | Passe par l'API |
