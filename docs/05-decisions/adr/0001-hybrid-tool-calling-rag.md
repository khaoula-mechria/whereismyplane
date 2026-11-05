# ADR-0001 — Approche hybride Tool Calling + RAG

- **Statut** : Acceptée (synthèse du projet, approche 3)
- **Date** : 2026-11-05 (formalisation)

## Contexte

L'assistant doit répondre à des questions de natures différentes : statistiques, prédictions et explications (données calculées), et définitions ou méthodologie (documentation). Un LLM seul peut produire des chiffres plausibles mais faux.

## Décision

Deux voies complémentaires orchestrées par Bedrock :
1. **Tool Calling** pour tout ce qui est chiffré ou prédictif, via des outils contrôlés (Athena, SageMaker).
2. **RAG** (Bedrock Knowledge Bases, optionnel) pour la documentation et les définitions.

## Alternatives écartées

| Alternative | Raison |
|---|---|
| RAG seul sur les données | Mauvais pour l'agrégation exacte ; confond documentation et résultats |
| LLM générant du SQL | Risque d'erreurs, d'injection et d'accès excessif (voir [ADR-0008](0008-llm-no-free-sql.md)) |
| Aucun LLM, interface à filtres seulement | Ne répond pas à l'objectif GenAI du projet |

## Conséquences

- (+) Chiffres traçables, comportement testable, séparation des responsabilités.
- (−) Sept outils à concevoir, valider et évaluer ; maintenance des schémas.
- Le RAG reste optionnel : le MVP fonctionne avec le Tool Calling seul. Le choix du magasin vectoriel est reporté à l'étape 9 (T9.2) après comparaison des coûts et des solutions disponibles (D-15 tranchée sur ce principe) ; le modèle Bedrock reste à choisir ([ADR-0012](0012-bedrock-model-selection.md)).
- Les outils sont écrits indépendamment de Bedrock pour être testables en local.
