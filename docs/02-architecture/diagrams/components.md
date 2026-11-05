# Diagramme de composants

## Backend applicatif

```mermaid
flowchart TB
    subgraph handlers ["api/ — gestionnaires Lambda"]
        hpred["handler /predict"]
        hstats["handler /stats/*"]
        hchat["handler /chat"]
        hmeta["handler /meta, /health"]
    end

    subgraph assistant ["assistant/"]
        orch["Orchestrateur<br/>boucle bornée"]
        prompts["Prompt système<br/>et règles"]
        bclient["Client Bedrock"]
    end

    subgraph tools ["tools/ — indépendants de Bedrock"]
        registry["Registre d'outils<br/>noms + schémas"]
        validate["Validation<br/>listes blanches"]
        t1["get_*_statistics (x4)"]
        t2["predict_flight_delay"]
        t3["explain_prediction"]
        t4["generate_delay_report"]
    end

    subgraph domain ["Domaine"]
        analytics["analytics/<br/>requêtes paramétrées"]
        features["features/<br/>variables T-2h"]
        config["config.py<br/>constantes, colonnes interdites"]
    end

    athenaC["Client Athena"]
    smC["Client SageMaker Runtime"]

    hchat --> orch
    orch --> prompts
    orch --> bclient
    orch --> registry
    registry --> validate
    registry --> t1 & t2 & t3 & t4
    hstats --> validate
    hstats --> t1
    hpred --> validate
    hpred --> t2
    t1 --> analytics --> athenaC
    t2 --> features --> smC
    t3 --> smC
    t4 -.entrée seule.-> t1
    features --> config
    analytics --> config
```

Les gestionnaires HTTP (`/stats`, `/predict`) et l'assistant appellent **les mêmes outils** : une seule implémentation, un seul chemin de validation.

## Pipeline de données et ML

```mermaid
flowchart LR
    ing["Ingestion"] --> clean["Nettoyage<br/>+ validation"] --> cat["Catalogue Glue"]
    clean --> agg["Agrégation"]
    clean --> feat["Variables T-2h<br/>+ cibles + split"]
    feat --> train["Entraînement<br/>3 modèles x 2 tâches"]
    train --> eval["Évaluation<br/>+ seuil"]
    eval --> gate{"Critères<br/>de qualité ?"}
    gate -- oui --> reg["Model Registry"]
    gate -- non --> stop["Rapport d'échec"]
    reg --> deploy["Endpoints"]
    train --> shap["SHAP"]
```

Voir aussi : [system-components.md](../system-components.md).
