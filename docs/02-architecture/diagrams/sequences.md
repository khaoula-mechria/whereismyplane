# Diagrammes de séquence

Les exemples de questions (aéroports, dates) sont illustratifs, sous réserve du contenu réel du dataset.

## 1. Prédiction (`POST /v1/predict`)

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant FE as Frontend
    participant AG as API Gateway
    participant LP as Lambda prédiction
    participant SC as Endpoint classification
    participant CW as CloudWatch

    U->>FE: Renseigne le vol
    FE->>AG: POST /v1/predict
    AG->>LP: requête
    LP->>LP: Valide (listes blanches, dates)
    alt entrée invalide
        LP-->>AG: 400 invalid_parameter
    else entrée valide
        LP->>LP: Construit les variables T-2h
        LP->>SC: InvokeEndpoint
        SC-->>LP: probabilité + SHAP
        LP->>LP: Applique le seuil
        LP-->>AG: 200 + prédiction + explications
    end
    LP->>CW: log (correlation_id, durée)
    AG-->>FE: réponse
    FE-->>U: Résultat + avertissement
```

## 2. Question analytique avec Tool Calling (`POST /v1/chat`)

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant AG as API Gateway
    participant LA as Lambda assistant
    participant BR as Bedrock
    participant TL as Outil (validation)
    participant AT as Athena

    U->>AG: "Quelle compagnie a le plus de retards à JFK en mars 2024 ?"
    AG->>LA: message
    LA->>BR: message + schémas d'outils + règles
    BR-->>LA: demande get_airline_delay_statistics(airport=JFK, from, to)
    LA->>TL: valide les paramètres
    alt paramètre refusé
        TL-->>LA: erreur de validation
        LA->>BR: résultat d'outil = erreur
    else paramètres acceptés
        TL->>AT: requête prédéfinie, paramètres liés, limite
        AT-->>TL: lignes agrégées
        TL-->>LA: données + source + période + n_flights
        LA->>BR: résultat d'outil
    end
    BR-->>LA: réponse rédigée à partir des résultats
    LA-->>AG: answer + sources
    AG-->>U: réponse
    Note over LA,BR: boucle limitée à N appels d'outils
```

## 3. Question documentaire (RAG, optionnel)

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant LA as Lambda assistant
    participant BR as Bedrock
    participant KB as Knowledge Base

    U->>LA: "Que signifie T-2h ?"
    LA->>BR: message + outils + accès documentaire
    BR->>KB: recherche
    KB-->>BR: passages + références
    BR-->>LA: réponse avec citation du document
    LA-->>U: réponse + source documentaire
```

## 4. Entraînement et promotion d'un modèle

```mermaid
sequenceDiagram
    actor M as Mainteneur
    participant PL as SageMaker Pipeline
    participant TR as Job d'entraînement
    participant EV as Évaluation
    participant RG as Model Registry
    participant EP as Endpoints

    M->>PL: Lance le pipeline
    PL->>TR: entraîne la classification
    TR-->>PL: modèles
    PL->>EV: métriques sur validation et test chronologiques
    EV-->>PL: métriques + seuil
    alt critères non atteints
        PL-->>M: échec + rapport
    else critères atteints
        PL->>RG: enregistre (statut en attente)
        M->>RG: approuve
        RG->>EP: déploiement
    end
    M->>EP: supprime après la démonstration
```
