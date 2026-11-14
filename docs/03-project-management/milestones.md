# Jalons

Un jalon est atteint uniquement lorsque tous ses critères de sortie sont vérifiés. Effort cumulé indicatif, en jours-personne (voir [implementation-plan.md](implementation-plan.md)).

| Jalon | Nom | Lots | Cumul indicatif | MVP |
|---|---|---|---|---|
| M0 | Fondations prêtes (dont estimation de coûts approuvée, **G0**) | WP0 | ≈ 4 j | Oui |
| M1 | Données prêtes | WP1, WP2 | ≈ 14 j | Oui |
| M2 | Jeu ML sans fuite | WP3 | ≈ 19 j | Oui |
| M3 | Modèles de référence | WP4 | ≈ 27 j | Oui |
| M4 | Modèles servis | WP5 | ≈ 35 j | Oui |
| M5 | Plateforme déployée par code | WP6 | ≈ 41 j | Oui |
| M6 | Application utilisable | WP7 | ≈ 49 j | Oui |
| **M7** | **MVP : assistant fiable** | WP8 | ≈ 57 j | **Oui — fin du MVP** |
| M8 | Extensions et clôture | WP9 | ≈ 63 j | Non |

Estimations indicatives sans marge ; date limite et temps disponible non fournis (U-03, U-08).

## Critères de sortie

| Jalon | Livrables | Critères (références) |
|---|---|---|
| M0 | Dépôt structuré, CI verte, AWS Budgets (50/80/100 % de 100 USD), config centrale, estimation de coûts approuvée | Lint et tests en CI ; AC-18 (budget), AC-25 ; **G0 franchi** |
| M1 | Source/licence documentées, `data-dictionary.md` complété, faisabilité T-2h établie, zones raw/processed/analytics, agrégats, requêtes paramétrées | AC-01, AC-02, AC-13, AC-23, AC-24 ; G1 franchi |
| M2 | `ml_dataset` avec découpage chronologique aux dates réelles | AC-03, AC-04 ; G2 franchi |
| M3 | Modèles, métriques, SHAP, rapport de modélisation, cibles de performance fixées (D-10) | AC-05, AC-06, AC-07 ; G3 franchi |
| M4 | Pipeline SageMaker, modèles dans le registry, un endpoint testé puis supprimé | AC-09, partie de AC-10 |
| M5 | Stacks CDK, parité Athena/DuckDB vérifiée, revue IAM | AC-12, AC-19 ; G4 franchi |
| M6 | API `/predict`, `/stats/*`, `/meta`, dashboard, formulaire, avertissements | AC-08, AC-10, AC-11, AC-20, AC-21 |
| M7 | Assistant avec 7 outils, jeu d'évaluation, chat dans l'interface | AC-14 à AC-17 ; G5 franchi |
| M8 | RAG évalué (si retenu), alarmes CloudWatch, démonstration documentée, ressources nettoyées | AC-22, AC-18 |

## Si un jalon est en retard

Ordre de réduction du périmètre, du moins au plus critique : (1) M8 entier ; (2) `generate_delay_report` en version minimale ; (3) ~~régression remplacée par classification seule~~ **fait : ADR-0017** ; (4) dashboard réduit à trois graphiques. Les AC-03, AC-04, AC-14 et AC-15 ne se négocient pas.
