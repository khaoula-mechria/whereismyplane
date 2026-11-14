# Conception de la sécurité

Principes confirmés : moindre privilège IAM, chiffrement, aucun secret dans le code, accès limités aux buckets et endpoints, lecture seule pour les analyses. Région `us-east-1`. L'authentification est tranchée (D-05). Le reste est **[Proposé]**.

## 1. Actifs et menaces

| Actif | Menace | Mesure |
|---|---|---|
| Budget AWS | Abus de `/chat` et `/predict`, endpoints oubliés | Limitation de débit, plafond de boucle d'outils, AWS Budgets, arrêt des endpoints |
| Données | Accès public à S3, lecture excessive | Blocage d'accès public, politiques par rôle, chiffrement |
| LLM | Injection de prompt via la question ou le contenu récupéré | Outils à paramètres validés, aucun SQL libre, lecture seule, sorties d'outils traitées comme des données |
| LLM | Fuite de consignes, réponses hors périmètre | Prompt système restrictif, refus des questions hors sujet, Guardrails Bedrock en option |
| Identifiants | Clés dans le dépôt | Rôles IAM et OIDC pour la CI ; scan de secrets ; `.env` ignoré |
| API | Appels non autorisés, CORS ouvert | Clé d'API, CORS restreint, validation des entrées |

## 2. IAM

| Rôle | Autorisations (résumé) |
|---|---|
| Lambda analyse | Athena (workgroup dédié), lecture Glue/S3 des zones processed et analytics, écriture sur athena-results |
| Lambda prédiction | `sagemaker:InvokeEndpoint` sur l'endpoint de classification uniquement |
| Lambda assistant | `bedrock:InvokeModel`/Converse sur le modèle choisi ; invocation des autres Lambdas/outils ; Knowledge Base en lecture si retenue |
| Rôle d'exécution SageMaker | Lecture `analytics/`, écriture `models/` |
| Rôle Glue | Lecture raw, écriture processed/analytics |
| Rôle CI | Déploiement CDK limité, via OIDC ; pas de clé statique |

Règles : aucune ressource `*` sans justification écrite ; une revue des politiques avant chaque déploiement (AC-19).

## 3. Données

- Chiffrement au repos (S3, Athena, SageMaker) ; clés gérées par AWS en MVP, KMS dédié optionnel.
- TLS partout (API Gateway, CloudFront).
- Journalisation de l'accès aux buckets de données.
- Le jeu ne contient pas de données personnelles [Hypothèse A-06, à vérifier à l'inspection du dataset] ; les logs applicatifs ne stockent ni IP en clair prolongée ni contenu superflu des conversations. À réviser si l'hypothèse tombe.

## 4. Athena et requêtes

- Un workgroup dédié à l'application avec limite de données analysées par requête et chiffrement des résultats.
- Requêtes prédéfinies avec paramètres liés ; identifiants (compagnie, aéroport) validés contre les listes de `/v1/meta`, jamais concaténés.
- Plafond de lignes retournées.

## 5. LLM

- Quatre barrières successives : (1) prompt système, (2) schéma d'outil strict, (3) validation côté serveur de chaque paramètre, (4) permissions en lecture seule.
- Le contenu récupéré par RAG est une donnée, pas une instruction ; la réponse doit distinguer documentation et résultats analytiques.
- Nombre maximal d'appels d'outils et de jetons par requête.
- Journaliser les appels d'outils (nom, paramètres validés, durée) pour audit.
- Jeu de tests adversariaux (injection, demandes de SQL, demandes hors périmètre) dans l'évaluation de l'assistant ([testing-strategy.md](../04-quality/testing-strategy.md)).

## 6. Réseau

Pas de VPC en MVP (C-08). Si une ressource en nécessite un, privilégier des points d'accès privés plutôt que des NAT gateways coûteuses, et documenter l'exception.

## 7. Authentification (tranchée : D-05)

| Option | Avantage | Inconvénient | Décision |
|---|---|---|---|
| Clé d'API + limitation de débit | Simple, bon marché | Clé visible côté client, protection limitée | **Retenue pour le MVP** |
| Cognito | Vrais comptes, jetons | Complexité, hors périmètre MVP | Reportée |
| Accès restreint par IP/WAF | Efficace pour une démo | Peu flexible, coût du WAF à estimer | Non retenue |

La limitation de débit est aussi une mesure de **protection du budget** (100 USD/mois) : Bedrock et SageMaker sont facturés à l'usage. Voir [ADR-0013](../05-decisions/adr/0013-mvp-api-usage-scope.md).

## 7 bis. Sécurité financière

Les alertes AWS Budgets (50 %, 80 %, 100 %) ne coupent pas les dépenses : une vérification régulière des ressources actives est requise ([cost-estimate.md](../04-quality/cost-estimate.md)). Rôles de déploiement sans droit de créer des ressources hors liste prévue, dans la mesure du possible.

## 8. Chaîne de livraison

Dépendances verrouillées, analyse des vulnérabilités en CI, revue des actions GitHub tierces, branche `main` protégée.
