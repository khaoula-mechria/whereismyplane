# Registre des décisions — AeroPulse

Mis à jour après l'arbitrage du propriétaire du projet. Statuts : **Tranchée**, **Tranchée sous condition**, **En attente de vérification**, **En attente d'information** (à fournir par le propriétaire). Une décision « Tranchée » n'est pas modifiée sans accord explicite.

Nom du projet : **AeroPulse** (anciennement FlightWise). Dataset : **NYC Flight Delays and Weather (2023–2025)** ([ADR-0010](adr/0010-dataset-nyc-2023-2025.md)) ; le dataset 2022 est abandonné.

## 1. Décisions

| ID | Décision retenue | Statut | ADR | Tâches | FR / AC |
|---|---|---|---|---|---|
| D-01 | Option A : dernière observation météo ≤ T-2h ; toute observation postérieure exclue. **Conditionnée** à des horodatages météo permettant de reconstruire T-2h ; sinon blocage signalé, sans donnée artificielle | **Tranchée sous condition** — vérification en attente | [0009](adr/0009-weather-at-t2h.md) | T1.5, T3.4, T3.7 | FR-07 / AC-03, AC-04 |
| D-02 | Saisie manuelle du vol **et** rejeu d'un vol de la période de test ; météo issue des données historiques disponibles à T-2h | Tranchée (dépend de D-01 pour la météo) | [0013](adr/0013-mvp-api-usage-scope.md) | T7.1, T7.3, T7.7 | FR-14, FR-16 / AC-10 |
| D-03 | CDK en Python | Tranchée | [0006](adr/0006-cdk-infrastructure-as-code.md) | T6.1 | NFR-02 / AC-12 |
| D-04 | React + Vite, bibliothèque de graphiques légère (choix précis à T7.5) | Tranchée | [0014](adr/0014-development-tooling.md) | T7.5–T7.7 | FR-16, FR-17 / AC-21 |
| D-05 | Pas de compte utilisateur en MVP ; clé d'API et limitation de débit | Tranchée | [0013](adr/0013-mvp-api-usage-scope.md) | T7.1, T7.4 | IR-02 / AC-19 |
| D-06 | SHAP calculé dans le script d'inférence SageMaker | Tranchée | [0007](adr/0007-sagemaker-two-endpoints.md) | T5.2 | FR-11 / AC-08 |
| D-07 | Endpoints temps réel temporaires (démonstrations, tests) ; évaluer l'inférence serverless | Tranchée (évaluation serverless à faire) | [0007](adr/0007-sagemaker-two-endpoints.md), [0011](adr/0011-region-budget-cost-guardrails.md) | T5.6, T5.7 | NFR-04 / AC-18 |
| D-08 | Seuil choisi sur la validation, F1 privilégié, rappel examiné | Tranchée | [0015](adr/0015-classification-threshold-selection.md) | T4.5 | FR-10 / AC-07 |
| D-09 | Pas d'historique des prédictions en MVP | Tranchée | [0013](adr/0013-mvp-api-usage-scope.md) | T7.1 | — |
| D-10 | Objectifs provisoires : p95 `/predict` < 3 s, p95 `/stats` < 10 s ; à confirmer après les premières mesures | Tranchée (provisoire) | — | T7.8 | NFR-05 / AC-11 |
| D-11 | uv pour les dépendances Python | Tranchée | [0014](adr/0014-development-tooling.md) | T0.2 | NFR-09 |
| D-12a | Région AWS : `us-east-1` | Tranchée | [0011](adr/0011-region-budget-cost-guardrails.md) | T6.1 | — |
| D-12b | Budget : 100 USD/mois max ; AWS Budgets à 50 %, 80 %, 100 % | Tranchée | [0011](adr/0011-region-budget-cost-guardrails.md) | T0.6, T0.8 | NFR-04 / AC-18 |
| D-12c | Modèle Amazon Bedrock | **En attente de vérification** (disponibilité en `us-east-1`, Tool Calling, coût, français, fonctionnalités RAG) | [0012](adr/0012-bedrock-model-selection.md) | T8.1 | FR-19 / AC-14–AC-16 |
| D-13 | Rapports en Markdown ou JSON ; PDF hors périmètre initial | Tranchée | [0013](adr/0013-mvp-api-usage-scope.md) | T8.3 | FR-22 / AC-17 |
| D-14 | Conserver `docs/ROADMAP.md` et `docs/PROGRESS.md` ; `03-project-management/roadmap.md` = vue par livrables ; ne pas dupliquer | Tranchée | — | T0.7 | — |
| D-15 | RAG optionnel ; magasin vectoriel décidé à l'étape 9 après comparaison des coûts et solutions | Tranchée (choix du magasin différé) | [0001](adr/0001-hybrid-tool-calling-rag.md) | T9.2, T9.3 | FR-23 / AC-22 |
| D-16 | Seuil minimal de 30 vols pour afficher une statistique | Tranchée | [0013](adr/0013-mvp-api-usage-scope.md) | T2.7, T7.2 | IR-01 / AC-13 |
| D-17 | Séparation chronologique adaptée au dataset retenu : entraînement 2023 + partie de 2024, validation fin 2024, test 2025 ; dates exactes après inspection | Tranchée (principe) — **dates en attente de vérification** | [0004](adr/0004-chronological-split.md) | T3.6 | FR-07 / AC-05–AC-07 |

| D-18 | **Stratégie d'acquisition du dataset** : reconstruction locale depuis BTS + NOAA Global Hourly avec cutoff T-2h (option B) ; échantillon Mostly Right de 500 lignes comme recette ; pas d'abonnement ; prévisions hors MVP | **Tranchée (approuvée le 2026-11-06)** — le téléchargement complet attend la lecture des licences | [0016](adr/0016-dataset-acquisition-strategy.md) | T1.1–T1.6, T2.1–T2.5 | FR-26, FR-27 / AC-23, AC-24 |
| D-19 | Traitement des vols **annulés / déroutés** : proposition = exclus des cibles ML, conservés dans les statistiques descriptives avec indicateur (cas d'un vol annulé avec retard renseigné à comprendre) | **Tranchée (approuvée le 2026-11-06)** | [0016](adr/0016-dataset-acquisition-strategy.md) | T1.4, T3.2 | FR-06 / AC-05, AC-06 |

Note : l'arbitrage a d'abord indiqué de ne pas figer région, modèle et budget (D-12), puis fourni la région et le budget. Le modèle Bedrock reste explicitement non choisi.

## 2. Éléments encore bloqués

### En attente d'information (à fournir par le propriétaire)

| Information | État | Bloque |
|---|---|---|
| Source du dataset | **Identifiée** : Mostly Right (`nyc_flight_delays_ml`) ; sources d'origine BTS et NOAA Global Hourly | — |
| Fichier complet du dataset | **Non téléchargé** (abonnement refusé) ; remplacé par la reconstruction (D-18) | Approbation de D-18 |
| Licence NOAA Global Hourly | **Lue le 2026-11-06** : ouverte, attribution demandée | — |
| Licence BTS On-Time | **Aucun texte lu** (403), aucune restriction trouvée : **acceptation du risque résiduel par le propriétaire requise** avant le téléchargement complet | T1.1 (AC-23) |
| Approbation de D-18 (stratégie d'acquisition) et de D-19 (annulés/déroutés) | **Reçue le 2026-11-06** | — |
| Date limite du projet (U-03) | Non fournie | Calendrier réel ; priorisation si retard |
| Temps disponible, taille de l'équipe (U-08) | Non fournis | Estimations (A-01 conservée comme hypothèse) |
| Accès à un compte AWS | Non confirmé | T0.6, T8.1 et phases AWS |
| Langue de l'interface | Français proposé (U-09) ; anglais ultérieur | Confirmation formelle en T7.1 |

### En attente de vérification technique

| Vérification | Comment | Bloque |
|---|---|---|
| Caractéristiques annoncées du dataset (1 056 897 vols, 33 variables, JFK/EWR/LGA, 2023-01 → 2025-07) | Inspection du fichier réel (T1.2) | Remplacement des valeurs annoncées par les valeurs réelles |
| Horodatages météo et reconstruction à T-2h | Test de [dataset-card.md](../dataset-card.md) section 4 (T1.5) | T3.4, T3.7 (partie météo), météo du mode de prédiction D-02 |
| Dates exactes du découpage | Couverture mensuelle (T1.2) puis T3.6 | T3.6, WP4 |
| Modèle Bedrock | ADR-0012, T8.1 | T8.5 à T8.8 |
| Estimation des coûts ≤ 100 USD/mois (point G0) | [cost-estimate.md](../04-quality/cost-estimate.md), T0.8 | Tout déploiement AWS payant (WP5 à WP9) |
| Inférence serverless SageMaker | T5.7 | Choix définitif d'hébergement |
| Magasin vectoriel du RAG | T9.2 | T9.3 |

## 3. Tâches qui ne doivent pas démarrer

| Tâche(s) | Condition de démarrage |
|---|---|
| Téléchargement complet BTS/NOAA (T1.1), puis WP2 | Licences BTS/NOAA lues et jugées compatibles (D-18 est approuvée) |
| T3.4, T3.7 (météo) | Faisabilité T-2h confirmée (D-01) |
| T3.6 | Couverture mensuelle vérifiée |
| T5.x à T9.x (déploiements) | Estimation de coûts approuvée (G0) |
| T8.5 → T8.8 | Modèle Bedrock vérifié et choisi (ADR-0012) |
| T9.3 | Magasin vectoriel décidé (T9.2) |

Tâches pouvant démarrer sans ces informations : T0.1 à T0.5, T0.7, T0.8 (hypothèses d'estimation), rédaction d'outils indépendants de Bedrock une fois WP2 terminé.

## 4. Traçabilité décision → exigences → critères

Voir les colonnes « Tâches » et « FR / AC » ci-dessus ; détail des tâches dans [task-breakdown.md](../03-project-management/task-breakdown.md), critères dans [acceptance-criteria.md](../01-planning/acceptance-criteria.md).
