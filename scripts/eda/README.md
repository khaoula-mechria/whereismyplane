# Scripts d'exploration T-2h (EDA)

Exploratoires : ils lisent **l'entraînement et la validation uniquement** (le jeu de test 2025 n'est pas chargé) et écrivent leurs fichiers intermédiaires dans `data/eda/` (non versionné). Rapport : [docs/04-quality/eda-report.md](../../docs/04-quality/eda-report.md).

Ordre d'exécution (depuis la racine, après `aeropulse.data.pipeline` et `aeropulse.features.build`) :

```bash
mkdir -p data/eda
uv run python scripts/eda/eda1.py              # cible, effets principaux, variabilité journalière
uv run python scripts/eda/eda2.py              # retards du jour connus avant T-2h, charge programmée
uv run python scripts/eda/eda3.py              # phénomènes météo NOAA (METAR), rafales
uv run python scripts/eda/eda4.py              # corrélations, dérive mensuelle
uv run python scripts/eda/fe_exp.py            # ablation des nouvelles variables (validation)
uv run python scripts/eda/fe_exp2.py           # seconde série + réglage
uv run --with matplotlib python scripts/eda/figs.py data/eda docs/04-quality/eda
```

Ces variables ne font **pas encore partie** du contrat `config.FEATURE_COLUMNS` : leur intégration dans `features/` (avec tests de non-fuite) attend une décision.
