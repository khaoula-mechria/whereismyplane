# Maîtrise et estimation des coûts

> Statut : **estimation réalisée le 2026-11-14 à partir des tarifs officiels `us-east-1` (AWS Price List) — en attente d'approbation du propriétaire (G0).** Les tarifs sont relevés, les volumes d'usage sont des **hypothèses** à valider ; les postes non relevés sont signalés. Contrainte validée : **budget maximal 100 USD/mois** (développement et démonstrations), région `us-east-1` ([ADR-0011](../05-decisions/adr/0011-region-budget-cost-guardrails.md)).

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

## 3. Tarifs relevés (source officielle, `us-east-1`, à la demande, hors offre gratuite)

Source : fichiers publics AWS Price List (`pricing.us-east-1.amazonaws.com/offers/v1.0/aws/<service>/current/us-east-1/index.json`), lus le 2026-11-14. Dates de publication des fichiers : S3 2026-11-09 · Glue 2026-11-08 · Athena 2026-09-11 · SageMaker 2026-11-14 · Lambda 2026-11-11 · API Gateway 2026-11-12 · CloudWatch 2026-11-04 · Secrets Manager 2026-11-11 · Bedrock (modèles de fondation) 2026-11-09. **L'offre gratuite n'est pas déduite** (estimation prudente). Les prix peuvent changer : recalculer à G0 et à chaque jalon.

| Service | Tarif relevé |
|---|---|
| S3 Standard | 0,023 USD/Go-mois (premiers 50 To) ; requêtes GET 0,004 USD / 10 000 |
| Glue (job ETL) | 0,44 USD/DPU-heure (version précédente) ; 0,308 USD/DPU-heure (Glue 6.0+) ; Flex 0,29 ; le plus cher est retenu |
| Athena | 5,00 USD/To analysé |
| SageMaker entraînement | ml.m5.xlarge 0,23 USD/h ; ml.m5.large 0,115 USD/h |
| SageMaker endpoint temps réel | ml.m5.large 0,115 USD/h ; ml.t2.medium 0,056 USD/h ; ml.c5.large 0,102 USD/h |
| SageMaker inférence serverless | 0,00006 USD/s (3 Go) ; 0,00002 USD/s (1 Go) ; 0,00012 USD/s (6 Go) |
| Lambda (x86) | 0,20 USD / million de requêtes ; 0,0000166667 USD/Go-seconde |
| API Gateway | REST 3,50 USD / million ; HTTP 1,00 USD / million |
| CloudWatch Logs | 0,50 USD/Go ingéré ; 0,03 USD/Go-mois stocké ; alarme 0,10 USD (poste à confirmer) |
| Secrets Manager | 0,40 USD/secret-mois ; 0,05 USD / 10 000 appels |
| Bedrock Claude Haiku 5.5 (régional, standard) | 0,11 USD / M jetons d'entrée ; 0,55 USD / M jetons de sortie |
| Bedrock Claude Sonnet 5.5 (régional, standard) | 2,20 USD / M jetons d'entrée ; 11,00 USD / M jetons de sortie |

**Non relevés (à compléter avant G0)** : CloudFront (transfert sortant), Bedrock Knowledge Bases et son magasin vectoriel (RAG optionnel, D-15), durée minimale de facturation et nombre minimal de DPU de Glue, transfert de données sortant S3/API. **La présence d'un modèle dans la liste tarifaire ne prouve pas sa disponibilité, le Tool Calling ni la qualité en français** : le choix du modèle reste en attente ([ADR-0012](../05-decisions/adr/0012-bedrock-model-selection.md)).

## 4. Hypothèses d'usage (à valider par le propriétaire)

| Hypothèse | Nominal | Pessimiste |
|---|---|---|
| Stockage S3 | 5 Go | 5 Go |
| Exécutions Glue (0,5 h, 2 DPU) | 4 / mois | 20 / mois |
| Données analysées par Athena | 2 Go | 50 Go |
| Entraînements SageMaker (ml.m5.xlarge) | 4 × 0,5 h | 20 × 1 h |
| Endpoints (2 × ml.m5.large) | 8 h de démonstration chacun | **oubliés une semaine** (168 h chacun) |
| Requêtes API (1 s, 1 Go de Lambda) | 20 000 | 200 000 |
| Logs CloudWatch | 2 Go, 5 alarmes | 10 Go, 5 alarmes |
| Secrets | 2 | 2 |
| Conversations de l'assistant | 300 × (10 000 jetons en entrée, 1 500 en sortie) | 3 000 × (30 000 en entrée, 4 000 en sortie) |

## 5. Estimation (USD/mois) — calcul reproductible à partir des tarifs et hypothèses ci-dessus

| Poste | Nominal | Pessimiste (endpoints 1 semaine) |
|---|---|---|
| S3 | 0,11 | 0,11 |
| Glue | 1,76 | 8,80 |
| Athena | 0,01 | 0,25 |
| SageMaker — entraînement | 0,46 | 4,60 |
| SageMaker — endpoints | 1,84 | **38,64** |
| Lambda | 0,34 | 3,37 |
| API Gateway (REST) | 0,07 | 0,70 |
| CloudWatch | 1,56 | 5,80 |
| Secrets Manager | 0,80 | 0,80 |
| **Sous-total hors Bedrock** | **6,95** | **63,08** |
| Bedrock, modèle de classe Haiku 5.5 | 0,58 | 16,50 |
| Bedrock, modèle de classe Sonnet 5.5 | 11,55 | **330,00** |
| **Total avec Haiku** | **7,53** | **79,58** |
| **Total avec Sonnet** | **18,50** | **393,08** |

Cas extrême (endpoints oubliés **tout le mois**, 2 × 730 h) : 167,90 USD pour les seuls endpoints, 208,84 USD au total avec Haiku, hors budget.

## 6. Comparaison à 100 USD/mois et conclusion proposée (G0 : décision du propriétaire)

| Question | Réponse chiffrée |
|---|---|
| Le scénario nominal tient-il ? | **Oui** : 7,53 USD (Haiku) ou 18,50 USD (Sonnet) |
| Le scénario pessimiste tient-il ? | **Avec un modèle de classe Haiku : oui** (79,58 USD, marge de 20 USD). **Avec un modèle de classe Sonnet : non** (393 USD) : le volume de conversations pessimiste coûte 330 USD |
| Les endpoints permanents tiennent-ils ? | **Non** : deux ml.m5.large permanents coûtent environ 168 USD/mois, plus que le budget entier |
| Qu'est-ce qui domine le risque ? | Les endpoints SageMaker oubliés, puis le volume de jetons Bedrock avec un modèle cher |

Conditions proposées pour lever G0 (à approuver ou amender par le propriétaire) :

1. **Aucun endpoint permanent.** Endpoints créés pour une démonstration puis supprimés (D-07), checklist exécutée à chaque session ; à comparer à l'**inférence serverless** (par exemple 3 Go à 0,00006 USD/s : 1,20 USD pour 20 000 requêtes d'une seconde, 12 USD pour 200 000). La compatibilité du serverless avec un script d'inférence personnalisé (prédiction + SHAP) **n'est pas vérifiée**.
2. **Modèle Bedrock de classe économique** par défaut, choix final dans ADR-0012 après vérification de disponibilité, Tool Calling et français.
3. **Plafonds applicatifs de jetons et de conversations** (limitation de débit, boucle d'outils bornée) : sans eux, un modèle plus cher fait dépasser le budget en usage intensif.
4. **Les alertes AWS Budgets ne coupent pas les dépenses** : elles ne protègent pas contre l'oubli d'un endpoint ; seule la discipline de suppression le fait.

## 7. Méthode d'estimation (rappel)

1. Hypothèses d'usage (§4) validées par le propriétaire.
2. Tarifs officiels `us-east-1` relevés et datés (§3) ; recalcul à G0.
3. Scénarios nominal et pessimiste (§5) ; le pessimiste doit rester sous le budget.
4. Approbation du propriétaire (G0), puis recalcul avec les coûts réels à chaque jalon.

## 8. Fonctionnalités susceptibles de dépasser le budget

| Fonctionnalité | Pourquoi | Alternative |
|---|---|---|
| Endpoints SageMaker permanents | Facturation continue | Endpoints temporaires, serverless à évaluer |
| Magasin vectoriel de la Knowledge Base | Coût de base potentiellement fixe | RAG optionnel, autre magasin, ou pas de RAG |
| Assistant très bavard ou boucle d'outils longue | Jetons | Plafonds, réponses courtes |
| NAT Gateway / VPC endpoints | Facturation à l'heure | Éviter le VPC (C-08) |
| Entraînements SageMaker répétés | Heures d'instance | Réglage local d'abord |
| Jobs Glue fréquents | Heures d'exécution | Exécutions ponctuelles |

## 9. Suivi

| Date | Mois | Dépense observée | Ressources actives | Commentaire |
|---|---|---|---|---|
| — | — | — | — | Aucune ressource AWS déployée |
