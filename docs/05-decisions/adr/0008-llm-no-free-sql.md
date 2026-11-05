# ADR-0008 — Pas de SQL libre pour le LLM

- **Statut** : Acceptée (synthèse du projet)
- **Date** : 2026-11-05 (formalisation)

## Contexte

Donner au LLM un accès SQL permettrait de répondre à tout, mais au prix d'erreurs silencieuses, de lectures coûteuses et de risques d'injection de prompt.

## Décision

Le LLM ne voit que des **outils nommés** avec des paramètres typés. Chaque outil :
- exécute une requête **prédéfinie** avec paramètres liés ;
- valide ses paramètres contre des **listes blanches** ;
- plafonne les lignes retournées ;
- utilise des permissions **en lecture seule** sur un workgroup Athena dédié.

L'assistant cite la source et la période de chaque chiffre et ne répond pas aux questions qu'aucun outil ne couvre.

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Text-to-SQL avec garde-fous | Garde-fous difficiles à prouver ; coût imprévisible |
| Vues préparées interrogeables librement | Reste un accès libre aux données |

## Conséquences

- (+) Exactitude vérifiable (AC-14), sécurité défendable (AC-15).
- (−) Couverture limitée aux sept outils : les questions inattendues reçoivent une réponse de limite ; nouveaux outils ajoutés au besoin.
