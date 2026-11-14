# Diagramme de flux de données

## Flux d'ensemble (batch)

```mermaid
flowchart TD
    src[("NYC Flight Delays and Weather<br/>2023–2025, format à vérifier")] -->|"1. ingestion"| raw[("S3 raw")]
    raw -->|"2. nettoyage, validation"| proc[("S3 processed<br/>Parquet")]
    proc -->|"3. déclaration"| cat["Glue Data Catalog"]
    proc -->|"4. agrégats"| ana[("S3 analytics<br/>agg_*")]
    proc -->|"5. variables T-2h<br/>historique strictement antérieur"| ml[("S3 analytics<br/>ml_dataset + split")]
    ml -->|"6. entraînement"| mdl[("S3 models<br/>+ Registry")]
    mdl -->|"7. déploiement"| ep["Endpoints SageMaker"]
    ana --> ath["Athena"]
    cat --> ath
    ath -->|"8a. statistiques"| api["API / outils"]
    ep -->|"8b. prédictions + SHAP"| api
    api --> ui["Dashboard et chat"]
```

## Où se situe la frontière T-2h

```mermaid
flowchart LR
    subgraph avant ["Disponible à T-2h : autorisé"]
        a1["compagnie, origine, destination, distance"]
        a2["heure programmée, jour de la semaine"]
        a3["dernière observation météo ≤ T-2h<br/>(sous condition D-01)"]
        a4["statistiques de vols dont le départ précède T-2h"]
    end
    subgraph apres ["Connu après T-2h : interdit"]
        b1["heure réelle de départ"]
        b2["retard réel au départ"]
        b3["heure réelle d'arrivée, retard d'arrivée"]
        b4["observations météo postérieures à T-2h"]
    end
    avant --> model["Modèle"]
    apres -. bloqué par le test de non-fuite .-> model
```

## Flux d'une prédiction (données)

```mermaid
flowchart LR
    in["Entrée utilisateur"] --> val["Validation<br/>listes blanches"]
    val --> fe["Construction des variables<br/>(même code qu'à l'entraînement)"]
    fe --> c["Classification"]
    c --> merge["Seuil + SHAP + version"]
    merge --> out["Réponse"]
```

Les statistiques historiques utilisées à la prédiction sont lues dans la zone analytics (valeurs figées à la date de fin d'entraînement) [Proposé] ; sinon une prédiction recalculerait des agrégats pendant l'appel.

Voir aussi : [er-diagram.md](er-diagram.md), [database-design.md](../database-design.md).
