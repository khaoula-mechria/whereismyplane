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

### Lecture des baselines

- Les baselines sont faibles par construction ; elles servent de plancher chiffré, pas d'objectif. Les cibles chiffrées de performance (D-10) ne sont **pas encore fixées** : elles le seront après T4.6, en fonction de ce que les modèles obtiennent (AC-05/AC-06 sont relatifs à la baseline jusque-là).
- La validation (juillet–décembre 2024) n'a pas la même saisonnalité que le test (janvier–juillet 2025) : les métriques de validation ne se transposent pas telles quelles au test.
- Aucune prévision météo n'est utilisée : la météo est la dernière observation ≤ T-2h (D-01).

## 3. Premiers modèles (T4.2, T4.3) — mesurés sur la validation

Commande : `uv run python -m aeropulse.models.train` (sortie : `data/ml/model_results.json`, non versionné). Ajustés sur l'entraînement (621 512 vols), évalués sur la validation (205 657), **test non lu**. Hyperparamètres de départ, **non réglés** (T4.4) : forêts de 100 arbres (profondeur 14, feuille ≥ 50), XGBoost (profondeur 6, pas 0,08, arrêt anticipé sur la validation : 86, 28 et 114 arbres).

### Classification (seuil F1-optimal choisi sur la validation)

| Modèle | PR-AUC | ROC-AUC | F1 | Précision | Rappel | Temps |
|---|---|---|---|---|---|---|
| Baseline aéroport × heure | 0,279 | 0,643 | 0,374 | 0,257 | 0,690 | — |
| Régression logistique | 0,376 | 0,705 | 0,418 | 0,329 | 0,572 | 9 s |
| Random Forest | **0,386** | 0,712 | 0,419 | 0,327 | 0,585 | 28 s |
| XGBoost | 0,382 | **0,716** | **0,426** | 0,330 | 0,600 | 23 s |

### Régression (minutes)

| Modèle | MAE | RMSE | Erreur abs. médiane | Temps |
|---|---|---|---|---|
| Baseline médiane aéroport × heure | 19,31 | 56,41 | 5,0 | — |
| Régression linéaire | 23,59 | 53,05 | 13,7 | 22 s |
| Random Forest (erreur quadratique) | 23,70 | 52,92 | 13,0 | 104 s |
| XGBoost, erreur quadratique | 24,00 | **52,83** | 13,6 | 4 s |
| XGBoost, erreur absolue | **18,83** | 54,49 | 5,5 | 10 s |

## 4. Lecture (à valider ; aucune cible D-10 fixée)

- **Classification** : les trois modèles battent nettement la baseline (PR-AUC 0,376–0,386 contre 0,279 ; prévalence 0,191). L'écart entre eux est faible (0,01 de PR-AUC) : le choix se fera sur le réglage (T4.4) et la robustesse, pas sur ces chiffres. Les gains absolus restent modestes (ROC-AUC ≈ 0,71) : le retard à T-2h est difficile à prédire avec ces variables.
- **Régression : le critère AC-06 (battre la baseline en MAE) n'est satisfait que par XGBoost à erreur absolue** (18,83 contre 19,31, soit −2,5 %). Les modèles entraînés sur l'erreur quadratique ont un meilleur RMSE mais une **MAE pire que la médiane globale** (19,42) : ils prédisent des moyennes tirées par la queue de gros retards. Le choix de la fonction de perte compte plus que le type de modèle. L'objectif réel (MAE ou RMSE, ou une approche en deux étapes) est à décider avant T4.6.
- **Biais optimiste connu** : l'arrêt anticipé de XGBoost et le seuil F1 utilisent la validation ; leurs métriques de validation sont légèrement favorables. L'évaluation finale sur le test sera la mesure sans biais.
- Les modèles n'ont pas encore de réglage, de gestion explicite du déséquilibre, ni de calibration.

## 5. À venir

T4.4 déséquilibre et réglage sur la validation · T4.5 seuil et métriques complètes · T4.6 évaluation finale unique sur le test · T4.7 SHAP · T4.8 cibles de performance (G3) · T4.9 artefacts.
