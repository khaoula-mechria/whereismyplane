# ADR-0018 — Architecture du déploiement AWS de test : inférence dans la Lambda, bundle S3 promu depuis le Model Registry

- **Statut** : **Proposée le 2026-11-21**, à confirmer par le propriétaire. Implémentée (code, IaC, tests) mais **non déployée** à cette date : les identifiants AWS du poste sont refusés par AWS (`InvalidClientTokenId`)
- **Date** : 2026-11-21
- **Déclencheur** : demande du propriétaire (« faire tout le pipeline et le déployer sur AWS (test), même si le modèle n'est pas optimisé »)
- **Modifie** : [ADR-0007](0007-sagemaker-two-endpoints.md) (endpoint temporaire → aucun endpoint), [ADR-0002](0002-s3-glue-athena-parquet.md) (job ETL Glue → étape SageMaker Processing ; Glue reste le catalogue), D-06 (SHAP calculé dans la Lambda, pas dans un script d'inférence SageMaker)
- **S'appuie sur** : l'image Lambda testée en local (option A, 2026-11-14), [ADR-0011](0011-region-budget-cost-guardrails.md), [cost-estimate.md](../../04-quality/cost-estimate.md)

## Contexte

- Le modèle retenu (XGBoost, `clf-f25ebbd328c5`) et le service de prédiction tournent déjà dans une image Lambda testée en local : p95 à chaud de 113 à 131 ms (émulateur), parité exacte avec l'entraînement.
- Un endpoint SageMaker temps réel coûte en continu (ml.m5.large ≈ 84 USD/mois s'il est oublié, 84 % du budget) et la règle du projet interdit d'en laisser un actif.
- Le pipeline de préparation existe en pandas/DuckDB, testé ; le réécrire en PySpark pour un job Glue demanderait une seconde implémentation à garder en parité, pour 1 million de lignes traitées en moins d'une minute sur un poste.
- Le jeu de test a déjà servi (T4.6) : il ne peut pas servir de garde-fou automatique à chaque entraînement.

## Décision

1. **Inférence dans la Lambda** (`POST /v1/predict`, `GET /v1/health`) : modèle en processus, SHAP exact de XGBoost, **aucun endpoint SageMaker**. Le contrat `ModelBackend` permet de brancher un endpoint plus tard sans toucher l'API.
2. **Bundle de service versionné** : une archive `tar.gz` (`release/` + `serving/` + `bundle.json`), vérifiée par SHA-256 à chaque chargement. C'est exactement le `model.tar.gz` produit par l'entraînement SageMaker. La Lambda lit le pointeur `s3://<données>/releases/current.json`, télécharge le bundle, le vérifie et le garde en cache ; elle relit le pointeur au plus toutes les 5 minutes. Un nouveau modèle ne demande donc **pas** de reconstruire l'image.
3. **Pipeline SageMaker** `aeropulse-training` : `Prepare` (Processing : `data.pipeline` + `features.build` + `serving_tables`, code local réutilisé tel quel) → `Train` (Training : `models.final` + `models.release`) → `Evaluate` (Processing : contrôle D-22 **sur la validation**, plus les tests de non-fuite exécutés dans l'image) → `QualityGate` → `Register` (Model Registry, **approbation manuelle**) ou `QualityFailed`.
4. **Promotion** : l'approbation d'un paquet déclenche (EventBridge) une Lambda qui vérifie l'artefact, le copie sous `releases/<version>/` et met à jour le pointeur ; l'ancien pointeur est conservé (`previous.json`, retour arrière en une commande).
5. **Image d'exécution unique** (base AWS Lambda Python 3.13) pour les Lambdas et les jobs SageMaker : le même code de variables sert à l'entraînement et au service (R-18).
6. **Données** : un bucket privé ; le catalogue Glue déclare la table `flights` avec projection de partitions, et Athena dispose d'un workgroup plafonné à 1 Go analysé par requête. Les statistiques de l'API (`/v1/stats`, `/v1/meta`) utilisent le moteur DuckDB existant sur le Parquet copié depuis S3 ; Athena sert à l'analyse ad hoc et au contrôle de parité (T6.3), avec le même SQL (requêtes nommées générées par `analytics.queries`).
7. **Exposition** : API Gateway REST avec clé d'API et plan d'usage (5 req/s, rafale 10, 2 000 req/jour), derrière la même distribution CloudFront que la console de test : même origine, donc pas de CORS à ouvrir.

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Endpoint SageMaker temps réel temporaire (ADR-0007) | Coût continu tant qu'il existe, démarrage de plusieurs minutes avant chaque démonstration ; aucun gain fonctionnel pour un modèle de quelques Mo |
| Inférence serverless SageMaker | Compatibilité avec un script d'inférence personnalisé (prédiction + SHAP) non vérifiée (T5.7) ; démarrage à froid supplémentaire derrière celui de la Lambda |
| Modèle intégré à l'image Lambda (option A d'origine) | Chaque réentraînement imposerait de reconstruire et repousser une image de 2 Go ; aucun lien avec le Model Registry |
| Job Glue PySpark pour la préparation | Seconde implémentation du nettoyage et de la météo T-2h à maintenir en parité ; Glue 5 et Python 3.11+ non testés avec les dépendances verrouillées |
| `/v1/stats` via Athena à chaque requête | Latence de plusieurs secondes et code de suivi asynchrone ; même résultat que DuckDB sur 28 Mo |

## Conséquences

- (+) **Coût à l'arrêt quasi nul** : rien ne tourne sans requête ni exécution du pipeline. Une exécution dure quelques minutes de ml.m5.large par étape.
- (+) Chaîne complète traçable : données → modèle → contrôle → registre → approbation humaine → API. Le modèle servi est identifié dans chaque réponse (`model_versions`).
- (+) Vérifié en local le 2026-11-21 sur les données réelles : la chaîne `Prepare → Train → Evaluate` reproduit **à l'identique** le jeu ML et le modèle `clf-f25ebbd328c5` ; validation PR-AUC 0,390, contrôle D-22 réussi, 8 tests de non-fuite verts.
- (−) **Le contrôle D-22 automatique porte sur la validation**, sur laquelle le seuil a été choisi : il est légèrement optimiste. C'est un garde-fou, pas une mesure finale ; le test n'est pas réutilisé (ADR-0004).
- (−) Démarrage à froid de la Lambda : image de 2 Go, plus téléchargement et chargement du bundle (2,2 s en local hors réseau) ; la première requête après un déploiement peut dépasser le délai de 29 s d'API Gateway (à mesurer, T7.8).
- (−) Un modèle promu est servi au plus tard 5 minutes après l'approbation (conteneurs déjà démarrés).
- (−) Écarts documentaires : le composant « endpoint » des diagrammes et CMP-02 « job Glue » ne correspondent plus au déploiement de test ; à aligner si l'ADR est acceptée.
- Réversible : brancher un `ModelBackend` SageMaker et ajouter une étape d'endpoint au pipeline suffirait à revenir à ADR-0007.
