# AeroPulse (anciennement FlightWise) — Project brief

> Statut : décisions D-01 à D-17 arbitrées ; vérifications techniques en attente (dataset, météo T-2h, modèle Bedrock, coûts). Légende : **[Confirmé]** = arbitré ou issu de la synthèse ; **[Hypothèse A-xx]** = supposé ; **[Inconnu U-xx]** = information manquante ; **[À vérifier]** = annoncé, non contrôlé. Listes complètes dans [scope-and-constraints.md](scope-and-constraints.md).

## 1. Problème

Les retards de vols coûtent du temps et de l'argent aux passagers, aux compagnies et aux aéroports. Les données historiques de vols et de météo existent, mais elles sont difficiles à exploiter directement : il faut les nettoyer, les croiser, les modéliser, puis les rendre accessibles à des non-spécialistes.

AeroPulse répond à quatre questions :

| Question | Réponse apportée |
|---|---|
| Ce vol sera-t-il en retard de plus de 15 minutes ? | Classification (probabilité + décision) |
| De combien de minutes sera-t-il en retard ? | Régression (`dep_delay`, négatif = avance) |
| Pourquoi cette prédiction ? | Explications SHAP (influence, pas causalité) |
| Que disent les données sur une compagnie, un aéroport, un itinéraire ? | Statistiques calculées par Athena, présentées par un tableau de bord et un assistant |

## 2. Solution en une phrase

Une plateforme AWS qui combine un lac de données (S3/Glue/Athena), deux modèles ML déployés sur SageMaker, une API (API Gateway + Lambda), un tableau de bord web et un assistant conversationnel Bedrock fondé sur **Tool Calling + RAG** [Confirmé].

## 3. Contexte et nature du projet

- Projet **académique / MVP** combinant Data Engineering, ML, MLOps, Cloud AWS et GenAI [Confirmé].
- Jeu de données : **NYC Flight Delays and Weather (2023–2025)**, annoncé avec environ 1 056 897 vols, 33 variables, aéroports JFK, EWR et LGA, de janvier 2023 à juillet 2025 [Confirmé comme choix ; caractéristiques **À vérifier**, source exacte et licence en attente — U-01, U-12]. Le dataset initial de 2022 est abandonné ([ADR-0010](../05-decisions/adr/0010-dataset-nyc-2023-2025.md)).
- Pas de données temps réel : les prédictions portent sur des vols historiques ou saisis manuellement, pas sur les conditions actuelles [Confirmé comme limite].
- Cadre AWS : région `us-east-1`, budget maximal de 100 USD/mois [Confirmé].
- Interface en français, anglais ultérieur [Proposé par le propriétaire].
- Équipe et calendrier : non précisés [Inconnu U-08, U-03] ; la planification suppose une personne travaillant à temps partiel [Hypothèse A-01].

## 4. Utilisateurs visés [Hypothèse A-05]

| Profil | Besoin | Usage principal |
|---|---|---|
| Analyste / évaluateur | Explorer les retards par compagnie, aéroport, itinéraire | Dashboard, assistant |
| Utilisateur curieux (voyageur fictif) | Estimer le risque de retard d'un vol | Formulaire de prédiction |
| Mainteneur (le développeur) | Réentraîner, promouvoir, déployer, arrêter les ressources | Pipeline SageMaker, CDK |

## 5. Périmètre résumé

- **MVP** : étapes 1 à 8 de [ROADMAP.md](../ROADMAP.md) (données, modèles, SageMaker, CDK, API, dashboard, assistant avec Tool Calling).
- **Optionnel** : RAG (Bedrock Knowledge Bases), monitoring avancé.
- **Hors périmètre initial** : flux temps réel ou simulés, données aéronautiques récentes, rapports PDF, comptes utilisateurs, historique des prédictions.

Détail dans [scope-and-constraints.md](scope-and-constraints.md).

## 6. Résultats attendus

1. Un jeu de données propre et catalogué, sans fuite temporelle (T-2h).
2. Deux modèles évalués contre une baseline, expliqués par SHAP.
3. Une application web déployée par code (CDK), arrêtable pour limiter les coûts.
4. Un assistant qui ne répond avec des chiffres que s'ils proviennent d'un outil, en citant source et période.

## 7. Indicateurs de réussite

| Indicateur | Cible | Où est-ce défini |
|---|---|---|
| Absence de fuite de données | 0 colonne interdite dans les variables du modèle | [acceptance-criteria.md](acceptance-criteria.md) AC-03 |
| Modèles meilleurs que la baseline | Cible chiffrée fixée après l'étape 4 (T4.8) | AC-05, AC-06 |
| Chiffres de l'assistant exacts | 100 % des chiffres retrouvés dans la sortie d'un outil | AC-14 |
| Infrastructure reproductible | Déploiement et destruction par CDK sans étape manuelle | AC-12 |
| Coût maîtrisé | ≤ 100 USD/mois ; aucune ressource facturée active hors démonstration ; estimation approuvée avant déploiement | AC-18, AC-25 |

## 8. Documents liés

[vision-and-objectives.md](vision-and-objectives.md) · [requirements.md](requirements.md) · [architecture-overview.md](../02-architecture/architecture-overview.md) · [implementation-plan.md](../03-project-management/implementation-plan.md) · [Index](../README.md)
