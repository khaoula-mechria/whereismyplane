# Exigences

Priorités : **M** = MVP, **O** = optionnel. Les identifiants sont repris dans [acceptance-criteria.md](acceptance-criteria.md), [task-breakdown.md](../03-project-management/task-breakdown.md) et [testing-strategy.md](../04-quality/testing-strategy.md).

## 1. Exigences fonctionnelles

### Données

| ID | Exigence | Prio |
|---|---|---|
| FR-01 | Charger le jeu brut dans la zone raw sans le modifier | M |
| FR-02 | Produire la zone processed en Parquet : doublons supprimés, valeurs manquantes et incohérentes traitées, dates normalisées | M |
| FR-03 | Cataloguer les tables dans Glue et les rendre interrogeables par Athena | M |
| FR-04 | Produire des agrégats (compagnie, aéroport, itinéraire) dans la zone analytics, avec taille d'échantillon | M |
| FR-05 | Documenter chaque colonne (sens, type, disponibilité à T-2h) dans [data-dictionary.md](../data-dictionary.md) | M |
| FR-26 | Documenter la source exacte et la licence du dataset ; comparer les caractéristiques annoncées aux caractéristiques réelles ([dataset-card.md](../dataset-card.md)) | M |
| FR-27 | Vérifier que les horodatages météo permettent de reconstruire les observations disponibles à T-2h ; sinon signaler le blocage, sans créer de données artificielles (D-01) | M |

### Machine Learning

| ID | Exigence | Prio |
|---|---|---|
| FR-06 | Construire le jeu ML avec la cible `is_delayed` (`dep_delay > 15`) ; `dep_delay` (négatifs conservés) reste une valeur observée pour les statistiques, pas une cible (ADR-0017) | M |
| FR-07 | N'utiliser que des variables disponibles à T-2h (météo : dernière observation ≤ T-2h, sous condition FR-27) ; statistiques historiques calculées sur les vols antérieurs uniquement ; découpage chronologique adapté à la période réelle du dataset (D-17) | M |
| FR-08 | Entraîner et comparer trois modèles de **classification** contre une baseline (pas de régression, [ADR-0017](../05-decisions/adr/0017-regression-postponed.md)) | M |
| FR-09 | Produire les métriques de classification : Precision, Recall, F1, ROC-AUC, PR-AUC, Brier, calibration | M |
| FR-10 | Choisir le seuil de décision sur la validation en privilégiant le F1-score et en examinant le rappel (D-08, [ADR-0015](../05-decisions/adr/0015-classification-threshold-selection.md)) | M |
| FR-11 | Produire des explications SHAP par prédiction (top-k variables) et globales | M |
| FR-12 | Enregistrer les modèles validés dans le Model Registry avec leurs métriques | M |
| FR-13 | Déployer un endpoint de classification, et pouvoir le supprimer | M |

### Application

| ID | Exigence | Prio |
|---|---|---|
| FR-14 | `POST /predict` : accepter une saisie manuelle du vol **ou** le rejeu d'un vol de la période de test (D-02) ; valider l'entrée, appeler le modèle de classification, renvoyer probabilité, décision, explications (aucune durée de retard estimée, ADR-0017) | M |
| FR-15 | Endpoints de statistiques : global, aéroport, compagnie, itinéraire, avec filtres de période | M |
| FR-16 | Formulaire de prédiction dans l'interface | M |
| FR-17 | Tableau de bord : indicateurs globaux, graphiques par compagnie, aéroport, itinéraire | M |
| FR-18 | Afficher les limites des données (période, aéroports, SHAP ≠ causalité) | M |

### Assistant

| ID | Exigence | Prio |
|---|---|---|
| FR-19 | `POST /chat` : l'assistant choisit et exécute des outils parmi les sept définis (voir [api-design.md](../02-architecture/api-design.md)) | M |
| FR-20 | Les outils analytiques utilisent des requêtes prédéfinies/paramétrées avec filtres autorisés, limite de lignes et lecture seule | M |
| FR-21 | Toute réponse chiffrée cite source et période ; l'assistant refuse d'inventer et signale quand un outil n'a pas de donnée | M |
| FR-22 | `generate_delay_report` produit un rapport structuré (Markdown/JSON) à partir de résultats déjà calculés | M |
| FR-23 | Répondre aux questions documentaires par RAG, en distinguant documentation et résultats analytiques | O |

### Exploitation

| ID | Exigence | Prio |
|---|---|---|
| FR-24 | Journaliser les requêtes (sans données personnelles), les erreurs et la latence dans CloudWatch | M |
| FR-25 | Détecter la dérive des données et suivre la qualité quand des résultats réels existent | O |

## 2. Exigences non fonctionnelles

| ID | Catégorie | Exigence | Mesure proposée |
|---|---|---|---|
| NFR-01 | Reproductibilité | Pipeline de données et d'entraînement relançable de bout en bout ; graines et versions fixées | Deux exécutions donnent les mêmes métriques |
| NFR-02 | Reproductibilité | Infrastructure intégralement décrite en CDK | `deploy` puis `destroy` sans étape manuelle |
| NFR-03 | Sécurité | Moindre privilège, chiffrement au repos et en transit, aucun secret dans le dépôt | Revue IAM ; scan de secrets en CI |
| NFR-04 | Coût | Dépense ≤ 100 USD/mois ; AWS Budgets avec alertes à 50 %, 80 %, 100 % ; aucun endpoint actif hors démonstration ; estimation de coûts approuvée avant tout déploiement payant ; vérification régulière des ressources (les alertes ne coupent pas les dépenses) | Budget actif ; [cost-estimate.md](../04-quality/cost-estimate.md) complété ; liste des ressources vide hors usage |
| NFR-05 | Performance | Prédiction : p95 < 3 s hors démarrage à froid ; statistiques : p95 < 10 s | Mesure CloudWatch (objectifs provisoires, D-10, à confirmer après mesures) |
| NFR-06 | Fiabilité de l'assistant | Aucun chiffre sans outil ; boucle d'outils bornée | Jeu d'évaluation de l'assistant |
| NFR-07 | Explicabilité | Chaque prédiction accompagnée de ses contributions principales | Champ `explanation` non vide |
| NFR-08 | Qualité des données | Contrôles automatiques (schéma, nulls, plages, doublons) bloquants | Rapport de validation |
| NFR-09 | Maintenabilité | Code structuré par module, typé, lint et tests en CI | CI verte requise pour fusionner |
| NFR-10 | Testabilité | Outils de l'assistant testables sans AWS | Tests unitaires locaux avec DuckDB |
| NFR-11 | Observabilité | Logs structurés avec identifiant de corrélation | Présent dans chaque Lambda |
| NFR-12 | Accessibilité | Interface lisible sur mobile et navigable au clavier | Contrôle manuel (cible proposée) |
| NFR-13 | Localisation | Interface en français ; chaînes de texte centralisées pour permettre l'anglais plus tard | Revue de l'interface (langue à confirmer en T7.1) |

## 3. Exigences dérivées de choix implicites [Hypothèse]

| ID | Exigence | Pourquoi |
|---|---|---|
| IR-01 | Seuil minimal de 30 vols (D-16) pour afficher une statistique par itinéraire ou compagnie | Des combinaisons rares existeront même avec un grand volume |
| IR-02 | Clé d'API et limitation de débit sur l'API (D-05) | Protéger le budget (Bedrock, SageMaker) |
| IR-03 | Plafond de volume analysé par requête Athena | Protéger le coût |
| IR-04 | Jeu d'évaluation de l'assistant versionné dans le dépôt | Vérifier FR-21 sans jugement subjectif |
| IR-05 | Le modèle Bedrock est un paramètre de configuration, choisi après vérification en `us-east-1` ([ADR-0012](../05-decisions/adr/0012-bedrock-model-selection.md)) | Modèle non encore choisi |

## Liens

[use-cases.md](use-cases.md) · [acceptance-criteria.md](acceptance-criteria.md) · [system-components.md](../02-architecture/system-components.md)
