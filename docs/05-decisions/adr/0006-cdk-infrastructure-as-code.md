# ADR-0006 — AWS CDK pour l'infrastructure

- **Statut** : Acceptée — CDK (synthèse) et **langage Python** (D-03 tranchée)
- **Date** : 2026-11-05 (formalisation)

## Contexte

Infrastructure reproductible et versionnée, déployable et supprimable (NFR-02, NFR-04).

## Décision

AWS CDK, une stack par responsabilité : `DataStack`, `MLStack`, `BackendStack`, `FrontendStack`, `AIStack`, `MonitoringStack`, et `NetworkStack` seulement si nécessaire (C-08).

## Langage (décidé)

Python, pour rester dans un seul langage avec le reste du projet (D-03, approuvée). L'alternative TypeScript, plus documentée par la communauté CDK, est écartée. Région de déploiement : `us-east-1` ([ADR-0011](0011-region-budget-cost-guardrails.md)).

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Terraform | Hors choix confirmé ; moins intégré à l'écosystème AWS CDK |
| CloudFormation brut | Verbeux |
| Console manuelle | Non reproductible |

## Conséquences

- (+) Déploiement et destruction reproductibles, revue de l'IAM dans le code.
- (−) Courbe d'apprentissage ; certaines ressources SageMaker (pipeline, registry) peuvent être plus naturelles à créer via le SDK SageMaker que via CDK : frontière à fixer en T6.4.
- L'activation de l'accès au modèle Bedrock peut rester manuelle.
