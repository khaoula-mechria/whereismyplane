# Registre des risques

Probabilité (P) et impact (I) : 1 faible, 2 moyen, 3 élevé. Score = P × I. Évaluations **[Proposées]**, à réviser à chaque jalon.

| ID | Risque | P | I | Score | Mitigation | Déclencheur / suivi | Lot |
|---|---|---|---|---|---|---|---|
| R-01 | **Fuite de données** (heure réelle, météo postérieure, statistiques incluant le futur) → métriques faussement bonnes | 3 | 3 | 9 | Dictionnaire avec colonne T-2h, liste interdite centralisée, test automatique, calcul d'historique strictement antérieur | Métriques « trop belles » en WP4 | WP1, WP3 |
| R-02 | **Décalage météo** : observée à l'entraînement, indisponible ou différente à T-2h | 3 | 2 | 6 | ADR-0009 : dernière observation antérieure à T-2h ; documenter la limite | U-02, G1 | WP1, WP3 |
| R-03 | **Dérive et couverture** : test sur 2025 (partielle, jusqu'à juillet annoncé) ; comportement des retards pouvant changer entre 2023 et 2025 ; année de test incomplète | 2 | 2 | 4 | Test sur la période la plus récente ; examiner la stabilité entre validation et test ; affichage des limites ; ne pas extrapoler | Écart validation/test | WP4, WP7 |
| R-04 | **Déséquilibre de classes** : peu de vols retardés > 15 min | 2 | 2 | 4 | PR-AUC, poids de classes, seuil choisi sur validation | Prévalence mesurée en WP1 | WP4 |
| R-05 | **Dépassement du budget de 100 USD/mois** (endpoints oubliés, Bedrock, base vectorielle, Glue) ; **les alertes AWS Budgets ne coupent pas les dépenses** | 2 | 3 | 6 | Estimation approuvée avant déploiement (G0), alertes 50/80/100 %, vérification régulière des ressources actives, endpoints temporaires, plafonds de boucle LLM, limitation de débit, RAG optionnel | Alerte à 50 % ; checklist de [cost-estimate.md](../04-quality/cost-estimate.md) | WP0, tous |
| R-06 | **Modèle Bedrock** : disponibilité en `us-east-1`, Tool Calling, coût, quotas, activation | 2 | 3 | 6 | Vérification T8.1 ([ADR-0012](../05-decisions/adr/0012-bedrock-model-selection.md)) ; outils indépendants de Bedrock pour ne pas bloquer le reste | U-04 | WP8 |
| R-07 | **Hallucination ou injection de prompt** : chiffres inventés, contournement des règles | 2 | 3 | 6 | Tool Calling, listes blanches, lecture seule, jeu d'évaluation adversarial, AC-14/15 | Évaluation en WP8 | WP8 |
| R-08 | **Complexité SageMaker/CDK** plus longue que prévu | 2 | 2 | 4 | Valider tout en local d'abord ; stacks incrémentales ; script d'entraînement testé localement avant cloud | Retard sur M4 | WP5, WP6 |
| R-09 | **Coût ou lenteur Athena** (scans excessifs, requêtes répétées) | 1 | 2 | 2 | Parquet, partitions, agrégats pré-calculés, workgroup avec limite | Volume scanné | WP2, WP6 |
| R-10 | **Dérive du périmètre** (flux, PDF, monitoring avancé) | 2 | 2 | 4 | Périmètre MVP figé, extensions listées, ordre de réduction dans milestones.md | Nouvelles demandes | Tous |
| R-11 | **Coût fixe du magasin vectoriel** de la Knowledge Base | 2 | 2 | 4 | Vérifier les options et tarifs avant WP9 ; RAG optionnel ; suppression après démonstration | D-15 | WP9 |
| R-12 | **Délai d'intégration d'API Gateway** (≈ 29 s par défaut, à vérifier) dépassé par la boucle d'outils | 2 | 2 | 4 | Limiter les itérations, délais par outil, réponses concises ; envisager le streaming ou l'asynchrone si nécessaire | Latence du chat | WP8 |
| R-13 | **Démarrage à froid** (Lambda, endpoints) dégradant l'expérience | 2 | 1 | 2 | Mesurer ; message d'attente ; accepter pour le MVP | NFR-05 | WP7 |
| R-14 | **Disponibilité de la personne** (temps partiel, compétences multiples AWS/ML/GenAI) | 2 | 3 | 6 | Plan par jalons, livraisons incrémentales, réduction de périmètre planifiée | Retard cumulé | Tous |
| R-15 | **Disponibilité ou conformité du jeu de données** : fichier absent, caractéristiques réelles différentes des annonces (1 056 897 vols, 33 variables, JFK/EWR/LGA, 2023-01 → 2025-07) | 2 | 3 | 6 | Vérifier en T1.1/T1.2 ; mettre à jour les documents avec les valeurs réelles ; conserver une copie et le checksum | U-01, U-12 | WP1 |
| R-16 | **Attentes utilisateur** : croire à des prédictions en temps réel | 2 | 2 | 4 | Avertissements visibles (FR-18), formulation « modèle historique » | Retour de démonstration | WP7 |
| R-17 | **Volume insuffisant pour certaines combinaisons** (itinéraire × compagnie × période) → statistiques instables malgré un grand volume global | 2 | 1 | 2 | Seuil minimal de 30 vols (D-16), affichage de l'échantillon | Distribution en WP1 | WP2 |
| R-18 | **Décalage entraînement/service** (variables calculées différemment) | 2 | 3 | 6 | Bibliothèque de variables partagée, test de parité sur des exemples | Écart de prédiction local/cloud | WP4, WP5, WP7 |

| R-19 | **Horodatages météo inexploitables** : impossible de reconstruire les observations disponibles à T-2h (météo fournie seulement au moment du départ, ou sans heure d'observation) | 2 | 3 | 6 | Test de faisabilité T1.5 ([dataset-card.md](../dataset-card.md) §4) ; en cas d'échec : blocage signalé, **aucune donnée artificielle**, arbitrage du propriétaire (source externe, sans météo, autre dataset) | AC-24 | WP1, WP3 |
| R-20 | **Licence du dataset** non vérifiée ou incompatible avec l'usage ; source exacte non documentée | 2 | 3 | 6 | T1.1 avant toute utilisation dans le dépôt ; aucun fichier versionné | A-02, U-12 | WP1 |
| R-21 | **Volumétrie sous-estimée pour les coûts** (Glue, Athena, stockage) si le dataset réel est plus gros que annoncé | 1 | 2 | 2 | Relever la taille réelle en T1.2 ; réviser [cost-estimate.md](../04-quality/cost-estimate.md) | Taille du fichier | WP1, WP2 |

## Top à surveiller

R-01 (9), puis R-02, R-05, R-06, R-07, R-14, R-15, R-18, R-19, R-20 (6 chacun). Revue du registre à chaque jalon (M0 à M8).

## Hypothèses du registre

Les scores supposent une personne seule, un compte AWS et un budget de 100 USD/mois. La date limite et la disponibilité (U-03, U-08) ne sont pas connues : réévaluer R-14 dès qu'elles le sont.
