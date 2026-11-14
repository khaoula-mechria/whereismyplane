# AeroPulse — Feuille de route (anciennement FlightWise)

> Document stable : décrit **toutes les étapes**. L'avancement se suit dans [PROGRESS.md](PROGRESS.md).
> Statut : **brouillon à réviser** (à relire avant le début de l'étape 1).

## Principes non négociables

- Prédiction à **T-2h** : aucune information postérieure à cet instant dans les variables.
- Séparation train / validation / test **chronologique**.
- Le LLM n'invente aucun chiffre : tout passe par des outils contrôlés (pas de SQL libre).
- **Local d'abord** : valider données et modèles avant d'activer des ressources AWS payantes.
- Dataset de référence NYC Flight Delays and Weather (2023–2025), JFK/EWR/LGA ; vols issus du Parquet Mostly Right (compte Pro du propriétaire, ADR-0016 amendé le 2026-11-13) ; météo **reconstruite depuis NOAA Global Hourly** avec cutoff T-2h, car le fichier publié a un cutoff de T-1h. Caractéristiques à vérifier sur les données réelles ; couverture et limites à signaler dans l'interface.
- **Pas d'abonnement** ; pas de prévisions météo dans le MVP (observations uniquement).
- **Budget** : 100 USD/mois maximum, région `us-east-1` ; aucun déploiement payant avant estimation des coûts ([cost-estimate.md](04-quality/cost-estimate.md)).

## Périmètre

- **MVP : étapes 1 à 8** (l'étape 9 est partiellement optionnelle).
- **Extensions (non démarrées)** : flux simulés (à présenter comme simulation), données aéronautiques récentes, rapports PDF automatiques, monitoring avancé.

## Étapes

### Étape 1 — Acquérir, explorer et vérifier le dataset
- **Où** : local (aucun coût AWS ; Parquet Mostly Right téléchargé avec le compte Pro du propriétaire)
- **Dépend de** : [ADR-0016](05-decisions/adr/0016-dataset-acquisition-strategy.md) (amendé : Parquet Mostly Right + NOAA ; BTS optionnel ; étude : [data-acquisition-study.md](data-acquisition-study.md)). **Faite en local le 2026-11-13**
- **Résultat attendu** : schéma et qualité des données connus.
- **Critères de fin** :
  - Parquet Mostly Right et NOAA Global Hourly téléchargés (BTS optionnel), tailles et sommes de contrôle consignées ;
  - volumes réels vérifiés (vols par mois, aéroports, période) et comparés aux chiffres publiés par Mostly Right (annoncés, non vérifiés) ;
  - source exacte et **licences BTS/NOAA** documentées ([dataset-card.md](dataset-card.md)) ;
  - test de réplication sur l'échantillon public de 500 lignes (2023-01-01) réussi ;
  - possibilité de reconstruire la météo disponible à T-2h vérifiée sur les observations NOAA (sinon : blocage signalé, aucune donnée artificielle) ;
  - `docs/data-dictionary.md` complété : chaque colonne avec sa signification, son type et sa disponibilité à T-2h ;
  - problèmes de qualité listés (doublons, valeurs manquantes, incohérences).

### Étape 2 — Pipeline de préparation
- **Où** : local (Parquet, DuckDB en remplacement d'Athena)
- **Dépend de** : 1
- **Résultat attendu** : données propres et documentées.
- **Critères de fin** :
  - doublons, valeurs manquantes et incohérences traités ;
  - dates et horaires normalisés ;
  - zones raw / processed / analytics en Parquet ;
  - pipeline relançable de bout en bout.

### Étape 3 — Variables T-2h et cibles
- **Où** : local
- **Dépend de** : 2
- **Résultat attendu** : dataset ML sans fuite de données.
- **Critères de fin** :
  - cibles `is_delayed` (`dep_delay > 15`) et `dep_delay` (négatifs conservés) ;
  - choix météo à T-2h tranché et documenté (prévision ou dernière observation) ;
  - statistiques historiques calculées uniquement sur les vols antérieurs ;
  - test de non-fuite qui passe ;
  - découpage chronologique train / validation / test défini.

### Étape 4 — Modèles en local
- **Où** : local
- **Dépend de** : 3
- **Résultat attendu** : modèles et métriques de référence.
- **Critères de fin** :
  - classification : régression logistique, Random Forest, XGBoost ;
  - régression : reportée, pouvant être ajoutée plus tard ([ADR-0017](05-decisions/adr/0017-regression-postponed.md)) ;
  - métriques : Precision, Recall, F1, ROC-AUC, PR-AUC, Brier ;
  - comparaison à une baseline simple ;
  - explications SHAP produites pour le meilleur modèle.

### Étape 5 — Entraînement sur SageMaker
- **Où** : AWS (début des coûts)
- **Dépend de** : 4
- **Résultat attendu** : pipeline MLOps reproductible.
- **Critères de fin** :
  - pipeline : préparation, entraînement, métriques, contrôle qualité ;
  - modèles validés enregistrés dans le Model Registry ;
  - un endpoint de classification déployable et supprimable.

### Étape 6 — Infrastructure avec CDK
- **Où** : AWS
- **Dépend de** : 5 (peut démarrer en parallèle pour `DataStack`)
- **Résultat attendu** : services AWS déployables.
- **Critères de fin** :
  - stacks : Data, ML, Backend, Frontend, AI, Monitoring (Network seulement si nécessaire) ;
  - moindre privilège IAM, chiffrement, aucun secret dans le code ;
  - déploiement et destruction reproductibles.

### Étape 7 — API et dashboard
- **Où** : AWS
- **Dépend de** : 6
- **Résultat attendu** : application utilisable.
- **Critères de fin** :
  - flux de prédiction : frontend, API Gateway, Lambda, endpoints SageMaker ;
  - validation des entrées côté Lambda ;
  - dashboard avec statistiques par compagnie, aéroport et itinéraire.

### Étape 8 — Assistant Bedrock avec Tool Calling
- **Où** : AWS
- **Dépend de** : 7
- **Résultat attendu** : assistant analytique et prédictif.
- **Critères de fin** :
  - 7 outils : `get_flight_statistics`, `get_airport_delay_statistics`, `get_airline_delay_statistics`, `get_route_delay_statistics`, `predict_flight_delay`, `explain_prediction`, `generate_delay_report` ;
  - requêtes Athena paramétrées, filtres autorisés, limites de résultats, lecture seule ;
  - réponses avec source et période ;
  - SHAP présenté comme influence, pas comme causalité.

### Étape 9 — RAG et monitoring (partiellement optionnel)
- **Où** : AWS
- **Dépend de** : 8
- **Résultat attendu** : assistant documentaire et suivi.
- **Critères de fin** :
  - documentation et définitions métier indexées (Bedrock Knowledge Bases) si budget et temps le permettent ;
  - CloudWatch : logs, métriques, alertes ;
  - suivi de dérive (Model Monitor) en option.

## Risques à surveiller

- Fuite de données via la météo ou les statistiques historiques (le cutoff du dataset publié est T-1h, pas T-2h).
- Licence de la table Mostly Right non établie (`license` null ; usage local, pas de redistribution) ; licence NOAA lue (ouverte, attribution) ; prévisions archivées non disponibles ou non vérifiées.
- Volume limité par route et par compagnie : prévoir un seuil minimal d'échantillons dans les outils statistiques.
- Coûts AWS (plafond 100 USD/mois) : endpoints SageMaker laissés actifs, Knowledge Base, ressources oubliées. Les alertes AWS Budgets ne coupent pas les dépenses.
