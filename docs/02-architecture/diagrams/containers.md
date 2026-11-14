# Diagramme de conteneurs

Les unités déployables d'AeroPulse (région `us-east-1`) et leurs échanges. Les endpoints SageMaker sont temporaires (D-07).

```mermaid
flowchart LR
    user(["Utilisateur"])

    subgraph edge ["Diffusion"]
        cf["CloudFront"]
        s3web[("S3 frontend")]
    end

    subgraph app ["Application"]
        apigw["API Gateway"]
        lstats["Lambda analyse<br/>outils statistiques"]
        lpred["Lambda prédiction"]
        lchat["Lambda assistant<br/>boucle d'outils"]
    end

    subgraph ai ["IA"]
        bedrock["Bedrock<br/>modèle de langage"]
        kb["Knowledge Base<br/>optionnel"]
    end

    subgraph ml ["ML"]
        epc["SageMaker<br/>endpoint classification"]
        reg["Model Registry"]
        pipe["SageMaker Pipeline"]
    end

    subgraph data ["Données"]
        s3[("S3<br/>raw / processed / analytics")]
        glue["Glue<br/>catalogue + ETL"]
        athena["Athena<br/>workgroup applicatif"]
        s3docs[("S3 docs RAG")]
    end

    cw["CloudWatch<br/>logs, métriques, alertes"]

    user --> cf --> s3web
    user --> apigw
    apigw --> lstats
    apigw --> lpred
    apigw --> lchat
    lchat --> bedrock
    lchat --> lstats
    lchat --> lpred
    lchat -.-> kb
    kb -.-> s3docs
    lstats --> athena --> s3
    glue --> s3
    athena -.catalogue.-> glue
    lpred --> epc
    lpred --> epr
    pipe --> reg --> epc
    reg --> epr
    s3 --> pipe
    lstats --> cw
    lpred --> cw
    lchat --> cw
    epc --> cw
```

Légende : trait plein = flux MVP ; trait pointillé = optionnel ou métadonnée.

Remarque : la boucle d'outils peut appeler les fonctions d'analyse et de prédiction en direct (appel de bibliothèque dans la même Lambda ou invocation interne). Le choix (une Lambda ou plusieurs) est un détail d'implémentation à trancher en T7 selon la taille du paquet de déploiement et les besoins d'isolation IAM.

Voir aussi : [components.md](components.md), [system-components.md](../system-components.md).
