# CLAUDE.md — AeroPulse (anciennement FlightWise)

Plateforme de prédiction et d'analyse des retards de vols (S3/Glue/Athena, SageMaker, Lambda/API Gateway, Bedrock). Région `us-east-1`, budget maximal 100 USD/mois. **Phase actuelle : planification** — voir `docs/PROGRESS.md`.

## Au début de chaque session

1. Lire `docs/PROGRESS.md` (étape en cours, prochaines actions, blocages).
2. Consulter `docs/README.md` pour retrouver le bon document, `docs/05-decisions/decisions-pending.md` pour les décisions non tranchées.
3. Ne pas supposer qu'une décision « proposée » est acceptée.

## À la fin de chaque session

Mettre à jour `docs/PROGRESS.md` (étape, tâches faites, prochaines actions, ressources AWS actives).

## Règles non négociables

- Prédiction à **T-2h** : aucune information postérieure dans les variables. Les colonnes interdites sont définies à un seul endroit (`config`) ; ne jamais les contourner.
- Découpage train/validation/test **chronologique** ; le jeu de test sert une seule fois à l'évaluation finale.
- Le LLM n'invente aucun chiffre et n'a **aucun accès SQL libre** : outils nommés, paramètres validés par listes blanches, lecture seule, limites de lignes.
- **Local d'abord** (Parquet + DuckDB) ; ne pas créer de ressources AWS payantes sans demande explicite. Ne jamais laisser un endpoint SageMaker actif.
- Aucun secret dans le dépôt ; `.env` ignoré ; moindre privilège IAM.
- Dataset principal : NYC Flight Delays and Weather (2023–2025), JFK/EWR/LGA. Ses caractéristiques sont **annoncées, non vérifiées** tant que le fichier réel n'a pas été inspecté (`docs/dataset-card.md`). Ne pas présenter les résultats comme des prédictions en temps réel.
- **Aucune donnée, aucun résultat, aucun coût ni aucune configuration AWS inventés.** Si les horodatages météo ne permettent pas de reconstruire l'état à T-2h, signaler le blocage ; ne pas fabriquer de données.
- **Budget** : aucun déploiement AWS payant avant une estimation de coûts compatible avec 100 USD/mois (`docs/04-quality/cost-estimate.md`). Les alertes AWS Budgets ne coupent pas les dépenses : vérifier régulièrement les ressources actives.
- Modèle Bedrock non choisi tant que la disponibilité n'est pas vérifiée dans `us-east-1` (ADR-0012).
- Ne pas commencer une tâche dont une décision « En attente » est un prérequis (voir `docs/05-decisions/decisions-pending.md`).
- Distinguer toujours ce qui est confirmé, proposé, supposé ou inconnu.

## Conventions de travail

- Documentation et échanges en **français** ; identifiants de code en anglais.
- **Ne pas committer ni pousser** sauf demande explicite : proposer le message de commit, le propriétaire du dépôt commit lui-même.
- Toute décision structurante → nouvelle ADR dans `docs/05-decisions/adr/` et mise à jour de l'index.
- Les identifiants (FR, AC, T-x.y, D-xx…) doivent rester cohérents entre documents ; vérifier la traçabilité dans `docs/03-project-management/task-breakdown.md` après toute modification d'exigence.
- Ne pas implémenter avant que les décisions requises par le lot concerné soient tranchées (colonne « Requis avant » de `decisions-pending.md`).

## Structure du dépôt cible (voir `docs/02-architecture/system-components.md`)

`src/aeropulse/{config,data,features,models,analytics,tools,assistant,api}` · `pipelines/{glue,sagemaker}` · `infra/` (CDK) · `frontend/` · `tests/` · `docs/`.

Règles de dépendance : `tools/` ne dépend ni de Bedrock ni de `api/` ; `features/` est partagé entre entraînement et service ; seul `analytics/` contient du SQL.

## Commandes

Gestionnaire : **uv** (D-11). Depuis la racine du dépôt :

- `uv sync` — installer les dépendances (crée `.venv`, génère `uv.lock`)
- `uv run ruff check` / `uv run ruff format` — lint / formatage
- `uv run mypy` — typage strict
- `uv run pytest` — tests
- `uv run python scripts/check_secrets.py` — scan de secrets (aussi en CI)
- `uv run pre-commit install` — active les hooks (optionnel)

Constantes centrales (seuil 15 min, horizon T-2h, colonnes interdites, stations NOAA, seuil de 30 vols) : `src/aeropulse/config.py`. Ne pas dupliquer ces valeurs ailleurs.
