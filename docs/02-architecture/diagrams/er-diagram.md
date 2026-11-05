# Diagramme entité-relation (lac de données)

Colonnes **indicatives** : à confirmer à l'étape 1 (U-01) sur le dataset NYC 2023–2025, dont les 33 variables annoncées ne sont pas encore connues ([data-dictionary.md](../../data-dictionary.md)). Les noms `dep_delay` et les concepts viennent de la synthèse ; le reste est proposé. L'existence d'une table météo séparée (`WEATHER_OBS`) n'est pas établie.

```mermaid
erDiagram
    AIRLINES ||--o{ FLIGHTS_CLEAN : opere
    AIRPORTS ||--o{ FLIGHTS_CLEAN : origine
    AIRPORTS ||--o{ FLIGHTS_CLEAN : destination
    AIRPORTS ||--o{ WEATHER_OBS : observe
    FLIGHTS_CLEAN ||--o| ML_DATASET : derive
    AIRLINES ||--o{ AGG_AIRLINE_DELAY : resume
    AIRPORTS ||--o{ AGG_AIRPORT_DELAY : resume
    AIRPORTS ||--o{ AGG_ROUTE_DELAY : "origine / destination"

    AIRLINES {
        string airline_code PK
        string airline_name
    }
    AIRPORTS {
        string airport_code PK
        string airport_name
        string timezone
    }
    FLIGHTS_CLEAN {
        string flight_id PK
        string airline_code FK
        string origin FK
        string destination FK
        double distance
        timestamp scheduled_departure
        timestamp actual_departure "interdit en variable ML"
        double dep_delay "cible, négatif = avance"
        int year
        int month
    }
    WEATHER_OBS {
        string airport_code FK
        timestamp obs_time
        double temperature
        double wind_speed
        double visibility
        double precipitation
    }
    ML_DATASET {
        string flight_id PK
        double features "variables T-2h"
        int is_delayed "dep_delay > 15"
        double dep_delay
        string split "train, validation, test"
    }
    AGG_AIRLINE_DELAY {
        string airline_code
        string period
        int n_flights
        double delay_rate_15min
        double mean_dep_delay
    }
    AGG_AIRPORT_DELAY {
        string airport_code
        string period
        int n_flights
        double delay_rate_15min
        double mean_dep_delay
    }
    AGG_ROUTE_DELAY {
        string origin
        string destination
        string period
        int n_flights
        double delay_rate_15min
        double mean_dep_delay
    }
```

Les tables `AGG_*` sont dérivées de `FLIGHTS_CLEAN` ; elles ne portent pas de clé étrangère physique (Athena n'en impose pas), la relation est logique.

Voir aussi : [database-design.md](../database-design.md).
