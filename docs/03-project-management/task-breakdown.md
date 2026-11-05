# Décomposition des tâches

Légende : **Prio** P0 = chemin critique MVP, P1 = MVP, P2 = optionnel. **Effort** en jours-personne, indicatif (A-01). **Dép.** = dépendances. Les exigences et critères renvoient à [requirements.md](../01-planning/requirements.md) et [acceptance-criteria.md](../01-planning/acceptance-criteria.md). Jalons : [milestones.md](milestones.md).

## Tâches bloquées (ne pas démarrer)

Détail et conditions dans [decisions-pending.md](../05-decisions/decisions-pending.md), section 3.

| Tâches | Bloquées par |
|---|---|
| T1.1 à T1.6, WP2 | Fichier du dataset non localisé, source et licence non documentées (U-12) |
| T3.4, T3.7 (partie météo), météo du mode de prédiction D-02 | Faisabilité T-2h non établie (D-01 sous condition, T1.5) |
| T3.6 | Couverture mensuelle non vérifiée (T1.2) |
| T5.1 à T9.x (tout déploiement payant) | Estimation de coûts non approuvée (T0.8, point G0) |
| T8.5 à T8.8 | Modèle Bedrock non vérifié (T8.1, ADR-0012) |
| T9.3 | Magasin vectoriel non décidé (T9.2) |
| Calendrier détaillé | Date limite et temps disponible non fournis (U-03, U-08) |

## WP0 — Fondations (M0, ≈ 4 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T0.1 | Créer la structure du dépôt, `.gitignore`, `.env.example` | — | P0 | Arborescence | Aucune donnée ni secret suivi par git |
| T0.2 | Configurer uv et la version de Python (D-11, tranchée) | — | P0 | Fichier de projet + verrouillage | Installation reproductible |
| T0.3 | Lint, formatage, typage, pre-commit | T0.2 | P1 | Configuration | Commandes passent sur un dépôt vide |
| T0.4 | CI minimale (lint + tests + scan de secrets) | T0.3 | P1 | Workflow CI | CI verte sur `main` (AC-19 partiel) |
| T0.5 | Constantes centrales : seuil 15 min, horizon 2 h, colonnes interdites, dates de découpage | T0.1 | P0 | `config.py` | Utilisé par tous les modules |
| T0.6 | AWS Budgets : budget mensuel de 100 USD, alertes à 50 %, 80 % et 100 % (`us-east-1`) ; vérifier avant création que cette configuration n'entraîne pas de frais | Accès à un compte AWS (non confirmé) | P0 | Budget actif | AC-18 (partie budget) |
| T0.7 | Enregistrer les décisions D-01…D-17 et relire la documentation | — | P0 | [decisions-pending.md](../05-decisions/decisions-pending.md) à jour (fait) ; reste : lever les attentes listées | Plus aucune décision « en attente d'information » bloquante |
| T0.8 | Remplir [cost-estimate.md](../04-quality/cost-estimate.md) (tarifs officiels `us-east-1`, scénarios nominal et pessimiste), comparer à 100 USD/mois, faire approuver (**G0**) | T0.1 | P0 | Estimation approuvée | AC-25 |

## WP1 — Exploration (étape 1, ≈ 4 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T1.1 | Documenter la source exacte du dataset NYC 2023–2025 et sa licence ; obtenir le fichier, calculer un checksum | U-12 (informations du propriétaire) | P0 | [dataset-card.md](../dataset-card.md) complétée | AC-23, A-02 levée, R-15, R-20 |
| T1.2 | Profiler : schéma, volumétrie, couverture mensuelle, nulls, doublons, aéroports ; comparer aux valeurs annoncées (1 056 897 vols, 33 variables, JFK/EWR/LGA, 2023-01 → 2025-07) | T1.1 | P0 | Notebook/rapport | U-01 levée, AC-23 |
| T1.3 | Compléter [data-dictionary.md](../data-dictionary.md) avec « disponible à T-2h ? » par colonne | T1.2 | P0 | Dictionnaire | AC-01 |
| T1.4 | Analyser la distribution de `dep_delay`, la prévalence des retards > 15 min, la couverture par compagnie/itinéraire (nombre de combinaisons sous 30 vols) | T1.2 | P0 | Synthèse | R-04, R-17 chiffrés |
| T1.5 | Vérifier la faisabilité de D-01 (test de [dataset-card.md](../dataset-card.md) §4) ; mettre à jour ADR-0009 ; **si impossible : signaler le blocage, aucune donnée artificielle** | T1.3 | P0 | Rapport de faisabilité + ADR-0009 | AC-24, **G1** |
| T1.6 | Définir la clé de vol, la gestion des fuseaux horaires et la plage de données exposée | T1.3 | P0 | Note de conception | Utilisée en WP2 |

## WP2 — Pipeline de préparation (étape 2, ≈ 6 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T2.1 | Ingestion vers la zone raw locale (comptage, checksum) | T1.6 | P0 | Script | Lignes raw = source (AC-01) |
| T2.2 | Règles de nettoyage documentées et implémentées | T1.4 | P0 | Module + doc | AC-02 |
| T2.3 | Normalisation des dates et fuseaux | T1.6 | P0 | Module + tests | Dates valides |
| T2.4 | Contrôles de validation bloquants (schéma, plages, doublons) | T2.2 | P0 | Rapport de validation | NFR-08, AC-02 |
| T2.5 | Écriture Parquet partitionnée (processed) | T2.3, T2.4 | P0 | Fichiers | Relecture identique |
| T2.6 | Agrégats par compagnie/aéroport/itinéraire avec `n_flights` | T2.5 | P0 | Tables analytics | FR-04 |
| T2.7 | Module `analytics/` : requêtes paramétrées testées avec DuckDB ; seuil minimal de 30 vols (D-16) | T2.6 | P0 | Requêtes + tests | AC-13, AC-15 (partie) |
| T2.8 | Exécution de bout en bout + tests unitaires | T2.7 | P1 | Commande unique | NFR-01 |

## WP3 — Variables et cibles (étape 3, ≈ 5 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T3.1 | Contrat de variables : autorisées / interdites, par colonne | T1.5 | P0 | Liste dans `config` | Source unique |
| T3.2 | Construire les cibles `is_delayed` et `dep_delay` | T2.5 | P0 | Fonction + tests | FR-06 |
| T3.3 | Variables de base : compagnie, origine/destination, itinéraire, distance, heure, jour | T3.1 | P0 | Module `features/` | FR-07 |
| T3.4 | Jointure météo « as-of » : dernière observation ≤ T-2h (D-01, **uniquement si AC-24 est satisfait**) | T3.1, T1.5 | P0 | Variables météo | Aucune observation > T-2h |
| T3.5 | Statistiques historiques strictement antérieures | T3.3 | P0 | Variables | AC-04 |
| T3.6 | Découpage chronologique : entraînement 2023 + partie de 2024, validation fin 2024, test 2025 ; **dates exactes fixées d'après la couverture réelle** (D-17) | T3.3, T1.2 | P0 | Dates documentées | ADR-0004 appliquée |
| T3.7 | Test de non-fuite et tests de cas construits | T3.4, T3.5 | P0 | `test_leakage` | AC-03, AC-04 ; **G2** |
| T3.8 | Écriture de `ml_dataset` | T3.6, T3.7 | P0 | Table | FR-06 |

## WP4 — Modèles locaux (étape 4, ≈ 8 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T4.1 | Baselines (prévalence/majorité ; médiane ; heuristique aéroport × heure) | T3.8 | P0 | Métriques | Référence chiffrée |
| T4.2 | Classification : régression logistique, Random Forest, XGBoost | T4.1 | P0 | Modèles | FR-08 |
| T4.3 | Régression : linéaire, Random Forest, XGBoost | T4.1 | P0 | Modèles | FR-08 |
| T4.4 | Gestion du déséquilibre et réglage sur la validation | T4.2, T4.3 | P1 | Paramètres | Pas de réglage sur le test |
| T4.5 | Métriques complètes ; choix du seuil sur la validation (D-08) | T4.4 | P0 | Rapport | FR-09, FR-10, AC-07 |
| T4.6 | Évaluation finale sur le test (une seule fois) ; erreurs par segment | T4.5 | P0 | Rapport | AC-05, AC-06 |
| T4.7 | SHAP global et local | T4.6 | P0 | Graphiques + fonction | FR-11 |
| T4.8 | Fixer les cibles de performance (D-10) ; rapport de modélisation | T4.6 | P0 | Document | **G3** |
| T4.9 | Sauvegarde des artefacts ; bibliothèque `features/` partagée entraînement/service | T4.6 | P0 | Artefacts | R-18 |

## WP5 — SageMaker (étape 5, ≈ 8 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T5.1 | Scripts d'entraînement paramétrables, testés en local ; **aucun job payant avant G0** (T0.8) | T4.9, T0.8 | P0 | Scripts | Même résultat qu'en local |
| T5.2 | Script d'inférence personnalisé (prédiction + SHAP dans l'inférence, D-06 tranchée) | T4.7 | P0 | Script | Parité avec le local |
| T5.3 | Pipeline : préparation → entraînement → évaluation → condition → enregistrement | T5.1, T0.6 | P0 | Définition de pipeline | FR-12 |
| T5.4 | Seuils de qualité dans la condition (D-10) | T4.8, T5.3 | P0 | Condition | AC-09 |
| T5.5 | Model Registry avec approbation manuelle | T5.3 | P0 | Groupe de modèles | AC-09 |
| T5.6 | Déployer les deux endpoints et tester l'invocation | T5.5 | P0 | Endpoints | FR-13 |
| T5.7 | Procédure d'arrêt/suppression des endpoints ; évaluer l'inférence serverless (D-07) en mesurant coût et limites réels, sans les supposer | T5.6 | P1 | Procédure + note | AC-18 |

## WP6 — Infrastructure CDK (étape 6, ≈ 6 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T6.1 | Squelette CDK en Python (D-03), région `us-east-1`, nommage, étiquettes de coût | T0.2 | P0 | Application CDK | Synthèse réussie (sans déploiement avant G0) |
| T6.2 | `DataStack` : S3, Glue, workgroup Athena | T6.1, T2.5 | P0 | Stack | AC-12 partiel |
| T6.3 | Charger les données, exécuter l'ETL Glue, vérifier la parité DuckDB/Athena | T6.2 | P0 | Rapport de parité | FR-03 ; mêmes résultats d'agrégats |
| T6.4 | `MLStack` | T5.6, T6.1 | P0 | Stack | Déploiement reproductible |
| T6.5 | `BackendStack` (API, Lambdas, rôles) squelette | T6.1 | P0 | Stack | Rôles minimaux |
| T6.6 | `MonitoringStack` de base : logs, alarmes | T6.5 | P1 | Stack | FR-24 |
| T6.7 | Revue IAM/sécurité ; test `deploy` puis `destroy` | T6.2–T6.6 | P0 | Revue documentée | AC-12, AC-19 ; **G4** |
| T6.8 | `NetworkStack` seulement si une ressource l'exige | T6.5 | P2 | Stack ou note « non nécessaire » | C-08 |

## WP7 — API et dashboard (étape 7, ≈ 8 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T7.1 | Spécification OpenAPI selon D-02, D-05, D-09, D-13 (tranchées) ; confirmer la langue de l'interface (français, U-09) | T0.7 | P0 | Spécification | [api-design.md](../02-architecture/api-design.md) à jour |
| T7.2 | `/meta` et `/stats/*` via les outils d'analyse | T2.7, T6.5 | P0 | Lambdas | AC-13 |
| T7.3 | `/predict` : deux modes (saisie manuelle, rejeu d'un vol de test), validation, variables, appel des endpoints, fusion ; mode dépendant de la météo bloqué si AC-24 non satisfait | T5.6, T4.9, T1.5 | P0 | Lambda | AC-10 |
| T7.4 | Clé d'API, limitation de débit (protection du budget), CORS, erreurs communes, identifiant de corrélation | T7.2 | P1 | Configuration | AC-19, AC-20 |
| T7.5 | Squelette du frontend et `FrontendStack` | T7.1, T6.1 | P1 | Site déployé | Page servie via CloudFront |
| T7.6 | Dashboard de statistiques | T7.2, T7.5 | P1 | Pages | FR-17 |
| T7.7 | Formulaire de prédiction, explications, avertissements | T7.3, T7.5 | P1 | Page | FR-16, FR-18, AC-08, AC-21 |
| T7.8 | Tests d'intégration et mesure de latence | T7.3 | P1 | Rapport | AC-10, AC-11 |

## WP8 — Assistant (étape 8, ≈ 8 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T8.1 | Vérifier les modèles Bedrock réellement disponibles en `us-east-1` : Tool Calling, français, coût, quotas, fonctionnalités RAG ; comparer 2–3 candidats ; consigner le choix et sa justification dans [ADR-0012](../05-decisions/adr/0012-bedrock-model-selection.md) (D-12c) | T0.6, T0.8 | P0 | ADR-0012 complétée, accès activé | R-06 levé |
| T8.2 | Registre d'outils, schémas d'entrée, validation par listes blanches | T2.7 | P0 | `tools/` | AC-15 |
| T8.3 | Implémenter les 7 outils | T8.2, T7.3 | P0 | Outils testés sans AWS | FR-19, FR-20, AC-17 |
| T8.4 | Prompt système et règles de réponse (source, période, refus) | T8.2 | P0 | Prompt versionné | FR-21 |
| T8.5 | Orchestrateur borné : itérations max, délais, journalisation | T8.1, T8.3 | P0 | `assistant/` | R-12 |
| T8.6 | Route `/chat` et interface de chat | T8.5, T7.5 | P1 | Page + route | FR-19 |
| T8.7 | Jeu d'évaluation (≥ 20 questions + cas adversariaux) | T8.3 | P0 | Fichier versionné | IR-04 |
| T8.8 | Itérer jusqu'à satisfaire AC-14 à AC-17 | T8.5, T8.7 | P0 | Rapport d'évaluation | **G5** |

## WP9 — Extensions et clôture (étape 9, ≈ 6 j)

| ID | Tâche | Dép. | Prio | Livrable | Critère |
|---|---|---|---|---|---|
| T9.1 | Rédiger les documents du RAG (définitions, méthodologie, limites) | T8.8 | P2 | Documents | Cohérents avec ce dossier |
| T9.2 | Comparer magasins vectoriels et solutions RAG disponibles en `us-east-1`, estimer le coût vs budget restant, décider (D-15) | T8.1, T0.8 | P2 | Note + mise à jour ADR-0001 | R-11 |
| T9.3 | Knowledge Base et intégration à l'assistant | T9.1, T9.2 | P2 | Stack + code | FR-23 |
| T9.4 | Évaluation du RAG | T9.3 | P2 | Rapport | AC-22 |
| T9.5 | Tableau de bord CloudWatch, alarmes d'erreur et de latence | T6.6 | P1 | Tableau de bord | FR-24 |
| T9.6 | Model Monitor / suivi de dérive | T9.5 | P2 | Option | FR-25 |
| T9.7 | Revue finale, scénario de démonstration, nettoyage des ressources | T8.8 | P1 | Documentation de démonstration | AC-18 |

## Traçabilité exigences → tâches → critères

| Exigence | Tâches | Critères |
|---|---|---|
| FR-01, FR-05 | T2.1, T1.3 | AC-01 |
| FR-26 | T1.1, T1.2 | AC-23 |
| FR-27 | T1.5 | AC-24 |
| NFR-13 | T7.1, T7.5–T7.7 | AC-21 |
| FR-02, NFR-08 | T2.2–T2.5 | AC-02 |
| FR-03 | T6.2, T6.3 | AC-01, AC-12 (parité de lecture via Athena en T6.3) |
| FR-04, IR-01 | T2.6, T2.7 | AC-13 |
| FR-06, FR-07 | T3.1–T3.8 | AC-03, AC-04 |
| FR-08, FR-09, FR-10 | T4.1–T4.6 | AC-05, AC-06, AC-07 |
| FR-11 | T4.7, T5.2 | AC-08 |
| FR-12, FR-13 | T5.3–T5.6 | AC-09 |
| FR-14, FR-16 | T7.3, T7.7 | AC-10 |
| FR-15, FR-17, FR-18 | T7.2, T7.6, T7.7 | AC-13, AC-21 |
| FR-19–FR-22 | T8.2–T8.8 | AC-14–AC-17 |
| FR-23 | T9.1–T9.4 | AC-22 |
| FR-24, NFR-11 | T6.6, T7.4, T9.5 | AC-20 |
| FR-25 | T9.6 | — (optionnel) |
| NFR-01 | T2.8, T5.1 | Deux exécutions identiques |
| NFR-02 | T6.1–T6.7 | AC-12 |
| NFR-03 | T0.4, T6.7 | AC-19 |
| NFR-04 | T0.6, T0.8, T5.7, T9.7 | AC-18, AC-25 |
| NFR-05 | T7.8 | AC-11 |
| NFR-06 | T8.4, T8.7, T8.8 | AC-14 |
| NFR-07 | T4.7, T5.2, T7.7 | AC-08 |
| NFR-09 | T0.3, T0.4 | CI verte (AC-19 pour le scan de secrets) |
| NFR-10 | T2.7, T8.2, T8.3 | AC-15, AC-17 (tests locaux sans AWS) |
| NFR-12 | T7.5–T7.7 | Contrôle manuel (voir [testing-strategy.md](../04-quality/testing-strategy.md)) |
| IR-02, IR-03 | T7.4, T6.2 | Contrôle de configuration |
| IR-04 | T8.7 | AC-14 |
| IR-05 | T8.1 | ADR-0012 complétée |

## Traçabilité décisions → ADR → tâches → critères

Voir le tableau de [decisions-pending.md](../05-decisions/decisions-pending.md) (colonnes ADR, Tâches, FR / AC).
