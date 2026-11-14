# Rapport de modélisation (T4.5, T4.8) — en cours

> Document vivant, alimenté au fil du WP4. **Seules des métriques mesurées y figurent.** Le jeu de test n'est lu qu'une fois (T4.6) : aucun résultat de test n'apparaît ici avant cette étape.

## 1. Protocole

| Élément | Valeur |
|---|---|
| Horizon | T-2h ([ADR-0003](../05-decisions/adr/0003-t-minus-2h-horizon.md)) |
| Cible de classification | `is_delayed = dep_delay > 15` (strict), recalculée ; annulés/déroutés exclus (D-19) |
| Cible de régression | `dep_delay` en minutes |
| Découpage | entraînement 2023-01-01 → 2024-06-30 (621 512) · validation 2024-07-01 → 2024-12-31 (205 657) · test 2025-01-01 → 2025-07-31 (200 417, intact) |
| Ajustement / évaluation des baselines | entraînement / validation |
| Seuil de décision | choisi sur la validation, F1 privilégié, rappel et précision examinés (ADR-0015) |

## 2. Baselines (T4.1) — mesurées sur la validation

Commande : `uv run python -m aeropulse.models.baselines` (sortie : `data/ml/baselines.json`, non versionné).

### Classification (prévalence validation : 19,06 %)

| Baseline | PR-AUC | ROC-AUC | F1 | Précision | Rappel |
|---|---|---|---|---|---|
| Prévalence constante (tout « retardé ») | 0,191 | 0,500 | 0,320 | 0,191 | 1,000 |
| Taux de retard par aéroport × heure (seuil F1 = 0,194) | **0,279** | **0,643** | **0,374** | 0,257 | 0,690 |

La référence à battre pour AC-05 est la PR-AUC de **0,279** (validation) ; un classifieur sans information vaut la prévalence, 0,191. Le seuil de la baseline a été choisi sur la validation elle-même : sa valeur est donc légèrement optimiste, ce qui est prudent pour une référence.

### Régression (minutes de retard au départ ; médiane d'entraînement −3 min, moyenne 13,2 min)

| Baseline | MAE | RMSE | Erreur absolue médiane |
|---|---|---|---|
| Médiane globale (−3 min) | 19,42 | 56,78 | 5,0 |
| Moyenne globale (13,2 min) | 26,38 | 54,69 | 18,2 |
| Médiane par aéroport × heure | **19,31** | 56,41 | 5,0 |

La référence à battre pour AC-06 est la MAE de **19,31 min** (validation). La distribution est très asymétrique (beaucoup de vols en avance ou à l'heure, queue de retards longs) : la moyenne a un meilleur RMSE mais une bien moins bonne MAE que la médiane. MAE et RMSE doivent être lus ensemble.

## 3. Lecture et limites

- Les baselines sont faibles par construction ; elles servent de plancher chiffré, pas d'objectif. Les cibles chiffrées de performance (D-10) ne sont **pas encore fixées** : elles le seront après T4.6, en fonction de ce que les modèles obtiennent (AC-05/AC-06 sont relatifs à la baseline jusque-là).
- La validation (juillet–décembre 2024) n'a pas la même saisonnalité que le test (janvier–juillet 2025) : les métriques de validation ne se transposent pas telles quelles au test.
- Aucune prévision météo n'est utilisée : la météo est la dernière observation ≤ T-2h (D-01).

## 4. À venir

T4.2 classification (régression logistique, Random Forest, XGBoost) · T4.3 régression · T4.4 déséquilibre et réglage sur la validation · T4.5 seuil et métriques complètes · T4.6 évaluation finale unique sur le test · T4.7 SHAP · T4.8 cibles de performance (G3).
