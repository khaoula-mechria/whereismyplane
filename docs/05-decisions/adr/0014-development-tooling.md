# ADR-0014 — Outillage de développement : uv, React + Vite

- **Statut** : Acceptée
- **Date** : 2026-11-05
- **Décisions couvertes** : D-04, D-11 (et D-03 : voir [ADR-0006](0006-cdk-infrastructure-as-code.md))

## Décisions

| ID | Décision |
|---|---|
| D-11 | **uv** pour gérer les dépendances Python (environnement et fichier de verrouillage) |
| D-04 | **React + Vite** pour le frontend (application monopage statique, compatible S3 + CloudFront), avec une bibliothèque de graphiques légère |
| D-03 | AWS CDK en **Python** (voir ADR-0006) |

La langue principale de l'interface est le **français** (proposition du propriétaire), l'anglais pourra être ajouté ensuite ; à confirmer formellement lors de T7.1.

## À choisir plus tard

- Bibliothèque de graphiques précise (critère : légère, accessible) : T7.5.
- Gestionnaire de paquets du frontend (npm, pnpm…) : T7.5.
- Outil de qualité des données (pandera, etc.) : T2.4.

## Conséquences

- (+) Un langage dominant (Python) hors frontend, outillage récent et rapide.
- (−) Deux écosystèmes (Python, JavaScript) à maintenir, deux CI à prévoir.
- Impacts : T0.2 (uv), T6.1 (CDK Python), T7.5 (React + Vite).
