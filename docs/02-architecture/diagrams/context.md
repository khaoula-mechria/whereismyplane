# Diagramme de contexte système

Qui interagit avec AeroPulse, et avec quels systèmes externes.

```mermaid
flowchart TB
    user(["Utilisateur<br/>analyste, évaluateur, curieux"])
    maint(["Mainteneur<br/>entraîne, déploie, arrête"])
    ds[("Jeu de données<br/>NYC Flight Delays and Weather 2023–2025<br/>source externe à documenter, chargement ponctuel")]

    subgraph fw ["AeroPulse (AWS us-east-1)"]
        app["Plateforme AeroPulse<br/>statistiques, prédiction, explication, assistant"]
    end

    bedrock["Amazon Bedrock<br/>modèle de langage"]

    user -->|"Navigue, prédit, interroge"| app
    maint -->|"CDK, pipelines"| app
    ds -->|"Chargement batch"| app
    app -->|"Raisonnement et rédaction"| bedrock
```

Notes :
- Aucun flux temps réel ni source externe de données de vol en MVP (extension).
- Bedrock est un service AWS mais dessiné à part car il porte une dépendance (modèle non encore choisi, disponibilité en `us-east-1`, quotas : [ADR-0012](../../05-decisions/adr/0012-bedrock-model-selection.md)).
- Les caractéristiques du dataset (JFK/EWR/LGA, 2023–2025) sont annoncées et non vérifiées.

Voir aussi : [containers.md](containers.md), [architecture-overview.md](../architecture-overview.md).
