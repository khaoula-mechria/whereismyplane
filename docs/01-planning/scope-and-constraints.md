# Périmètre, contraintes, hypothèses et inconnues

Projet **AeroPulse** (anciennement FlightWise). Statuts : **Confirmé** (arbitré ou issu de la synthèse), **Tranché** (décision du propriétaire, voir [decisions-pending.md](../05-decisions/decisions-pending.md)), **Hypothèse**, **Inconnu**, **En attente de vérification**.

## 1. Périmètre

### Inclus (MVP)

1. Chargement et traitement du dataset historique **NYC Flight Delays and Weather (2023–2025)** ([ADR-0010](../05-decisions/adr/0010-dataset-nyc-2023-2025.md)).
2. Stockage S3 (raw / processed / analytics) et catalogue Glue.
3. Analyses SQL avec Athena.
4. Entraînement et comparaison de modèles de classification (la régression est **reportée**, pouvant être ajoutée plus tard : ADR-0017).
5. Déploiement des modèles validés sur SageMaker (endpoints temporaires).
6. Exposition des prédictions via API Gateway + Lambda, avec clé d'API.
7. Tableau de bord web (React + Vite, interface en français).
8. Assistant Bedrock avec Tool Calling.

### Optionnel (si temps et budget)

9. RAG documentaire (Bedrock Knowledge Bases), magasin vectoriel décidé à l'étape 9.
10. Monitoring avancé (Model Monitor, dérive).

### Hors périmètre initial

Flux temps réel ou simulés (une simulation serait présentée comme telle), données aéronautiques récentes, rapports PDF, comptes utilisateurs, historique des prédictions, aéroports autres que ceux du dataset, interface multilingue (anglais ultérieur).

## 2. Contraintes

| ID | Contrainte | Statut |
|---|---|---|
| C-01 | Horizon de prédiction fixe : T-2h | Confirmé |
| C-02 | Découpage train/validation/test chronologique, adapté à la période réelle du dataset | Confirmé (dates en attente de vérification) |
| C-03 | Données limitées à celles du dataset NYC 2023–2025 (JFK, EWR, LGA annoncés) | Confirmé (contenu **non vérifié**) |
| C-04 | LLM sans accès SQL libre ; requêtes paramétrées, lecture seule, limites de résultats | Confirmé |
| C-05 | Moindre privilège IAM, chiffrement, aucun secret dans le code | Confirmé |
| C-06 | Développement local d'abord ; ressources AWS payantes activées progressivement | Confirmé |
| C-07 | Infrastructure en AWS CDK (Python) | Tranché |
| C-08 | Réseau proportionné au MVP (pas de VPC complexe, pas de NAT Gateway sans besoin) | Confirmé |
| C-09 | Endpoints SageMaker temporaires, supprimés après usage | Tranché |
| C-10 | **Budget maximal 100 USD/mois** ; AWS Budgets à 50 %, 80 %, 100 % (les alertes ne coupent pas les dépenses) | Tranché |
| C-11 | Région AWS `us-east-1` | Tranché |
| C-12 | Aucun déploiement payant avant estimation de coûts approuvée (point G0) | Tranché |
| C-13 | Aucune donnée, résultat, coût ou configuration inventé ; aucune donnée artificielle si la météo à T-2h est irreconstructible | Tranché |

## 3. Hypothèses

| ID | Hypothèse | Impact si fausse |
|---|---|---|
| A-01 | Une personne, temps partiel, cadre académique ou portfolio, sans SLA de production | Estimations à revoir (temps et équipe non communiqués) |
| A-02 | La licence du dataset autorise l'usage prévu | **En attente de vérification** ; sinon changer de source |
| A-03 | Un compte AWS est disponible et suffisant pour les services listés | Phases AWS replanifiées |
| A-04 | Le dataset contient une météo avec horodatages exploitables pour reconstruire T-2h | **En attente de vérification** ; sinon blocage (ADR-0009) |
| A-05 | Utilisateurs : analystes/évaluateurs, sans comptes individuels | Tranché pour le MVP (D-05) ; Cognito ultérieurement |
| A-06 | Le dataset ne contient aucune donnée personnelle | À vérifier lors de l'inspection |
| A-07 | Python est le langage principal hors frontend | Tranché (D-03, D-11) |
| A-08 | Interface en français ; l'assistant répond dans la langue de la question | Proposé par le propriétaire, à confirmer (T7.1) |
| A-09 | Les caractéristiques annoncées du dataset (≈ 1 056 897 vols, 33 variables, JFK/EWR/LGA, 2023-01 → 2025-07) sont à peu près exactes | **En attente de vérification** ; documents à corriger avec les valeurs réelles |
| A-10 | Les ressources prévues sont disponibles dans `us-east-1` | À vérifier service par service avant déploiement |

## 4. Inconnues et informations à fournir

| ID | Question | État | Bloque |
|---|---|---|---|
| U-01 | Schéma exact, volumétrie réelle, valeurs manquantes, couverture mensuelle | En attente de vérification (T1.2) | WP2, T3.6 |
| U-02 | Météo à T-2h : horodatages exploitables ? | En attente de vérification (T1.5) | T3.4, T3.7 météo |
| U-03 | Date limite du projet | **Non fournie** | Calendrier |
| U-04 | Modèle Bedrock disponible en `us-east-1`, Tool Calling, coût | En attente de vérification ([ADR-0012](../05-decisions/adr/0012-bedrock-model-selection.md)) | T8.5–T8.8 |
| U-05 | Authentification | Tranché : clé d'API, sans comptes (D-05) | — |
| U-06 | Mode de saisie d'une prédiction | Tranché (D-02) | — |
| U-07 | Cibles de performance des modèles | À fixer après baselines (T4.8) | T5.4 |
| U-08 | Taille de l'équipe, temps disponible | **Non fournis** | Calendrier |
| U-09 | Langue de l'interface | Français proposé | T7.1 |
| U-10 | Langage CDK, framework frontend | Tranché (D-03, D-04) | — |
| U-11 | Historique des prédictions | Tranché : aucun (D-09) | — |
| U-12 | Source exacte, emplacement du fichier, licence du dataset | **Non fournis / à vérifier** | T1.1, T1.2 |
| U-13 | Estimation de coûts mensuels vs 100 USD | À produire (T0.8) | Déploiements AWS payants |

## 5. Limites à afficher à l'utilisateur

Provisoires, à confirmer après inspection du dataset :

- Les données couvrent le dataset NYC 2023–2025 (JFK, EWR, LGA annoncés), pas le trafic aérien complet.
- Une prédiction repose sur des données historiques : ce n'est pas une information en temps réel.
- La météo utilisée est une observation antérieure à T-2h, pas une prévision (sous réserve de D-01).
- Les contributions SHAP indiquent l'influence sur le modèle, pas une cause.
- Les statistiques sur moins de 30 vols ne sont pas affichées.

## Liens

[project-brief.md](project-brief.md) · [risk-register.md](../03-project-management/risk-register.md) · [decisions-pending.md](../05-decisions/decisions-pending.md) · [dataset-card.md](../dataset-card.md) · [cost-estimate.md](../04-quality/cost-estimate.md)
