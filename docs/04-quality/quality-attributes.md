# Attributs de qualité

Chaque attribut est relié à une exigence, une tactique d'architecture et une vérification. Les cibles de latence sont **provisoires** (D-10), à confirmer après mesures ; les cibles de qualité des modèles seront fixées en T4.8.

| Attribut | Importance | Exigence | Tactique | Vérification |
|---|---|---|---|---|
| **Exactitude / véracité** des chiffres | Critique | FR-21, NFR-06 | Tool Calling, requêtes prédéfinies, sources citées | AC-14, AC-17 |
| **Intégrité des données** (pas de fuite) | Critique | FR-07, NFR-08 | Contrat T-2h, tests de non-fuite, split chronologique | AC-03, AC-04 |
| **Sécurité** | Élevée | NFR-03 | Moindre privilège, listes blanches, lecture seule, OIDC pour la CI | AC-15, AC-19 |
| **Maîtrise des coûts** (100 USD/mois) | Élevée | NFR-04 | Budgets 50/80/100 %, estimation avant déploiement, endpoints temporaires, plafonds de boucle LLM, limitation de débit, vérification régulière | AC-18, AC-25 |
| **Reproductibilité** | Élevée | NFR-01, NFR-02 | Versions verrouillées, graines, IaC | AC-12 |
| **Explicabilité** | Élevée | NFR-07, FR-11 | SHAP, mention « pas de causalité » | AC-08 |
| **Performance** | Moyenne | NFR-05 | Parquet, agrégats pré-calculés, variables simples, appels parallèles aux endpoints | AC-11 : p95 `/predict` < 3 s ; `/stats` < 10 s (proposé) |
| **Fiabilité** | Moyenne | FR-24 | Erreurs explicites, délais d'expiration, 503 clair si endpoint arrêté | Tests d'intégration |
| **Observabilité** | Moyenne | NFR-11 | Logs structurés, identifiant de corrélation, métriques | AC-20 |
| **Maintenabilité** | Moyenne | NFR-09 | Modules à responsabilité unique, outils indépendants de Bedrock, ADR | Revue, CI |
| **Testabilité** | Moyenne | NFR-10 | Pas de dépendance AWS dans la logique métier | Tests locaux |
| **Utilisabilité** | Moyenne | FR-18 | Avertissements, messages d'échantillon insuffisant, réponses sourcées | AC-21 |
| **Accessibilité** | Basse | NFR-12 | Contrastes, navigation clavier, adaptation mobile | Contrôle manuel |
| **Disponibilité** | Basse | — | Pas de SLA : services managés, endpoints à la demande | — (A-01) |

## Compromis assumés

| Compromis | Choix |
|---|---|
| Coût vs disponibilité | Endpoints non permanents : disponibilité réduite acceptée, message 503 explicite |
| Simplicité vs sécurité d'accès | Clé d'API + limitation de débit, sans comptes (D-05) |
| Richesse de l'assistant vs fiabilité | Sept outils fermés plutôt qu'un accès libre aux données |
| Précision vs interprétabilité | Comparer régression logistique et arbres ; choisir sur métriques et lisibilité des explications |
| Fraîcheur vs reproductibilité | Données historiques figées (dataset NYC 2023–2025, période exacte à vérifier), assumé et affiché |
| Fonctionnalités vs budget | Plafond de 100 USD/mois : endpoints temporaires, RAG optionnel, assistant à jetons plafonnés |
