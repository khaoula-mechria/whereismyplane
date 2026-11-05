# Maîtrise et estimation des coûts

> Statut : **estimation non réalisée.** Aucun prix n'est affirmé dans ce document : les tarifs doivent être relevés dans l'AWS Pricing Calculator et les pages tarifaires officielles pour `us-east-1`, à la date de l'estimation. Contrainte validée : **budget maximal 100 USD/mois** (développement et démonstrations), région `us-east-1` ([ADR-0011](../05-decisions/adr/0011-region-budget-cost-guardrails.md)).

## 1. Règle d'or

**Aucune ressource AWS payante n'est déployée tant que cette estimation n'est pas remplie, comparée à 100 USD/mois et approuvée par le propriétaire (point G0).** Phases A et B (local) : coût AWS nul.

## 2. Garde-fous

| Garde-fou | Détail | Limite |
|---|---|---|
| AWS Budgets | Budget mensuel de 100 USD avec alertes à **50 % (50 USD), 80 % (80 USD), 100 % (100 USD)** (T0.6) | Les alertes **notifient**, elles ne coupent pas les dépenses |
| Vérification régulière | Contrôle des ressources actives (liste ci-dessous) à la fin de chaque session de travail et avant chaque démonstration | Dépend de la discipline ; consigné dans [PROGRESS.md](../PROGRESS.md) |
| Étiquettes de coût | Étiquette de projet sur chaque ressource ; Cost Explorer pour la lecture | — |
| Endpoints temporaires | SageMaker créés pour tests/démonstrations, supprimés ensuite (D-07) | Un oubli coûte en continu |
| Plafonds applicatifs | Limitation de débit, boucle d'outils bornée, taille de réponse bornée | Protège Bedrock et SageMaker |
| Arrêt automatique | **À étudier** (par exemple les actions de budget) ; ne pas supposer qu'un arrêt automatique est garanti pour tous les services | Non retenu tant que non vérifié |

### Contrôle des ressources actives (à exécuter régulièrement)

1. Endpoints SageMaker : aucun actif hors démonstration.
2. Jobs d'entraînement ou de traitement en cours.
3. Knowledge Base et son magasin vectoriel (si créés).
4. Jobs Glue et sessions de développement Glue.
5. Passerelles NAT, VPC endpoints, adresses IP élastiques (ne devraient pas exister, C-08).
6. Buckets : volumes inattendus, versions anciennes.
7. Coût du mois en cours et prévision dans Cost Explorer.

## 3. Estimation par service (à compléter avant G0)

Niveau de risque = potentiel de dépassement du budget si mal maîtrisé (évaluation qualitative, pas un coût).

| Service | Usage prévu | Facteur de coût | Risque | Maîtrise | Estimation (USD/mois) |
|---|---|---|---|---|---|
| S3 | Zones raw/processed/analytics, modèles, frontend, docs | Stockage, requêtes | Faible | Cycle de vie, pas de copies inutiles | À faire |
| Glue (ETL, catalogue) | Nettoyage, agrégats | Heures d'exécution des jobs | Moyen | Jobs courts, à la demande, tailles minimales ; valider d'abord en local | À faire |
| Athena | Requêtes statistiques | Données analysées par requête | Faible | Parquet, partitions, agrégats pré-calculés, limite par workgroup | À faire |
| SageMaker — entraînement | Jobs ponctuels | Heures d'instance | Moyen | Instances adaptées, jobs courts, essais en local d'abord | À faire |
| SageMaker — endpoints | 2 modèles | Heures d'instance **tant que l'endpoint existe** | **Élevé** | Création pour tests/démonstrations, suppression ensuite ; évaluer l'inférence serverless | À faire |
| Lambda | API, outils, assistant | Requêtes, durée | Faible | Limitation de débit | À faire |
| API Gateway | Exposition | Requêtes | Faible | Plans d'utilisation | À faire |
| CloudFront + S3 | Frontend | Transfert, requêtes | Faible | — | À faire |
| Bedrock (LLM) | Assistant | Jetons entrée/sortie | Moyen à élevé | Modèle économique adapté, réponses courtes, boucle d'outils bornée, limitation de débit | À faire (dépend du modèle, ADR-0012) |
| Bedrock Knowledge Bases | RAG (optionnel) | Embeddings, **magasin vectoriel** (coût de base possible) | **Élevé** (selon le magasin) | Optionnel, décision à l'étape 9 (D-15), comparaison des coûts, suppression après démonstration | À faire (si retenu) |
| CloudWatch | Logs, métriques, alarmes | Ingestion, rétention, alarmes | Faible à moyen | Rétention courte, logs sobres | À faire |
| Secrets Manager | Si nécessaire | Par secret | Faible | Parameter Store si suffisant | À faire |

## 4. Méthode d'estimation

1. Fixer les hypothèses d'usage : nombre de démonstrations par mois, durée d'existence des endpoints, requêtes `/predict`, `/stats`, `/chat` par mois, longueur moyenne d'une conversation, volume de données stocké, nombre d'exécutions Glue et d'entraînements.
2. Relever les tarifs officiels `us-east-1` pour chaque service (date du relevé consignée).
3. Calculer un scénario **nominal** et un scénario **pessimiste** (endpoint oublié une semaine, conversation longue).
4. Comparer au budget de 100 USD ; marge de sécurité recommandée avant G0 : le scénario pessimiste doit rester sous le budget, sinon revoir l'architecture.
5. Faire valider par le propriétaire (G0), puis recalculer avec les coûts réels observés à chaque jalon.

## 5. Fonctionnalités susceptibles de dépasser le budget

| Fonctionnalité | Pourquoi | Alternative |
|---|---|---|
| Endpoints SageMaker permanents | Facturation continue | Endpoints temporaires, serverless à évaluer |
| Magasin vectoriel de la Knowledge Base | Coût de base potentiellement fixe | RAG optionnel, autre magasin, ou pas de RAG |
| Assistant très bavard ou boucle d'outils longue | Jetons | Plafonds, réponses courtes |
| NAT Gateway / VPC endpoints | Facturation à l'heure | Éviter le VPC (C-08) |
| Entraînements SageMaker répétés | Heures d'instance | Réglage local d'abord |
| Jobs Glue fréquents | Heures d'exécution | Exécutions ponctuelles |

## 6. Suivi

| Date | Mois | Dépense observée | Ressources actives | Commentaire |
|---|---|---|---|---|
| — | — | — | — | Aucune ressource AWS déployée |
