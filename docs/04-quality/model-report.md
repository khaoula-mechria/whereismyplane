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

## 5. Réglage sur la validation (T4.4)

Commande : `uv run python -m aeropulse.models.tune` ; recherche aléatoire à graine fixe (42), **12 essais par tâche**, XGBoost, ajustement sur l'entraînement, sélection sur la validation, test non lu. Espace : profondeur 4–10, pas 0,03–0,1, `min_child_weight` 1–50, `subsample` 0,7–1, `colsample_bytree` 0,6–1, `reg_lambda` 1–20 ; pour la classification, aussi `scale_pos_weight` ∈ {1, 2, 4} (déséquilibre). Paramètres retenus : [tuned_params.json](../../src/aeropulse/models/tuned_params.json).

| Tâche | Avant réglage | Meilleur essai | Étendue des 12 essais |
|---|---|---|---|
| Classification (PR-AUC) | 0,382 | **0,390** (profondeur 4, pas 0,1, 151 arbres, `scale_pos_weight` = 1) | 0,371 – 0,390 |
| Régression (MAE, perte absolue) | 18,833 | **18,821** (profondeur 4, pas 0,1, 160 arbres) | 18,821 – 18,983 |

Lecture :

- **Gain de réglage faible** : +0,008 de PR-AUC et −0,012 min de MAE, du même ordre que la dispersion entre essais. Les modèles plafonnent : c'est l'information des variables, pas les hyperparamètres, qui limite la performance.
- **Les arbres peu profonds gagnent** (profondeur 4 meilleure en classification comme en régression, profondeur 10 la pire) : les modèles profonds sur-ajustent la période d'entraînement, ce qui est cohérent avec la dérive temporelle du retard (R-03).
- **Déséquilibre** : pondérer la classe minoritaire (`scale_pos_weight` 2 ou 4) n'améliore pas la PR-AUC (le meilleur essai utilise 1). Le déséquilibre (19 % de retards) est modéré ; l'ajustement du seuil F1 (T4.5) suffit à ce stade.
- **Optimisme** : 12 essais sélectionnés sur la validation, qui sert aussi à l'arrêt anticipé : la valeur de validation du meilleur essai est un peu favorable. Seul le test (T4.6) donnera une mesure sans biais.

## 6. Modèles figés, seuil et calibration (T4.5)

Commande : `uv run python -m aeropulse.models.final` ; les deux modèles XGBoost réglés sont réentraînés **sur l'entraînement seul** (nombre d'arbres fixé par le réglage, sans arrêt anticipé sur la validation) et sauvegardés dans `data/ml/models/` (`classifier.json`, `regressor.json`, `meta.json` : variables, catégories, seuil, paramètres ; non versionné). Test non lu.

### Classification, seuil choisi sur la validation (ADR-0015)

Seuil retenu : **0,200** (F1 maximal). Métriques de validation :

| PR-AUC | ROC-AUC | F1 | Précision | Rappel | Brier |
|---|---|---|---|---|---|
| 0,390 | 0,720 | 0,429 | 0,346 | 0,566 | 0,138 (référence prévalence : 0,154) |

Compromis précision/rappel autour du seuil (validation) :

| Seuil | Précision | Rappel | F1 |
|---|---|---|---|
| 0,10 | 0,249 | 0,863 | 0,386 |
| 0,15 | 0,299 | 0,713 | 0,421 |
| **0,20** | 0,346 | 0,566 | **0,429** |
| 0,25 | 0,389 | 0,450 | 0,417 |
| 0,30 | 0,431 | 0,354 | 0,388 |
| 0,40 | 0,506 | 0,207 | 0,294 |
| 0,50 | 0,570 | 0,104 | 0,176 |

Le seuil par défaut de 0,5 ne retiendrait que 10 % des retards : le seuil F1 est justifié. La probabilité brute reste à afficher avec la décision (ADR-0015).

### Calibration

- Sur l'entraînement, le modèle est calibré (probabilité moyenne 0,204 = fréquence observée 0,204).
- Sur la validation, il **sous-estime d'environ 1,2 point** (0,178 prédit contre 0,191 observé) : la fréquence observée dépasse la prédiction dans les 10 déciles. Ce n'est pas un défaut de code : le modèle suit la saisonnalité (juillet–août élevés, automne bas) mais le retard de fin 2024 est plus élevé que prévu (décembre : 0,187 prédit, 0,230 observé ; septembre : 0,152 prédit, 0,123 observé). C'est la **dérive temporelle** attendue (R-03) : les probabilités sont utilisables pour classer les vols, moins comme fréquences exactes. Une recalibration reste possible ; elle n'est pas faite.

### Régression (MAE, perte absolue ; validation)

MAE **18,82 min**, RMSE 54,45, erreur absolue médiane 5,57. Baseline : 19,31 min de MAE.

## 7. Explications SHAP (T4.7) — validation, modèle figé

Commande : `uv run python -m aeropulse.models.explain` (contributions exactes de XGBoost, en log-cotes ; échantillon de 30 000 vols de validation ; test non lu). Contrôle d'additivité : somme des contributions = marge du modèle, écart maximal 3·10⁻⁶. Chaque explication locale renvoie au moins 3 contributions (AC-08) avec la mention « influence sur la prédiction du modèle, pas une cause ».

Importance globale (contribution absolue moyenne) :

| Rang | Variable | Importance | Rang | Variable | Importance |
|---|---|---|---|---|---|
| 1 | heure de départ | 0,312 | 6 | itinéraire | 0,139 |
| 2 | taux de retard 28 j (aéroport × heure) | 0,203 | 7 | point de rosée | 0,138 |
| 3 | compagnie | 0,190 | 8 | taux de retard 28 j (aéroport) | 0,100 |
| 4 | mois | 0,164 | 9 | pression au niveau de la mer | 0,079 |
| 5 | taux de retard 28 j (compagnie) | 0,160 | 10 | plafond nuageux | 0,068 |

Par groupes : les **variables météo pèsent environ 27 %** de l'importance totale, les **taux historiques 25 %**, le reste vient du calendrier, de la compagnie et de l'itinéraire. La distance, l'aéroport d'origine et la destination comptent très peu (déjà captés par l'itinéraire et l'historique).

Lectures prudentes : (1) SHAP mesure l'influence sur le modèle, pas une cause ; (2) des variables corrélées (heure, historique aéroport × heure, saison) se partagent l'importance ; (3) l'importance du point de rosée peut refléter la saison ou le brouillard plus qu'un effet direct.

## 8. Évaluation finale sur le test (T4.6) — usage unique, 2026-11-14

Modèles, hyperparamètres et seuil (0,200) **figés avant** (T4.4–T4.5, empreintes SHA-256 des artefacts dans le rapport). Exécution unique de `aeropulse.models.final_evaluation` sur **200 417 vols (2025-01-01 → 2025-07-31)** ; un fichier de verrou interdit toute seconde exécution. Rapport brut : `data/ml/models/test_evaluation.json` (non versionné). Aucun résultat du test n'a servi à modifier quoi que ce soit.

### Classification (seuil 0,200 choisi sur la validation)

| | Modèle | Baseline aéroport × heure | Prévalence seule |
|---|---|---|---|
| PR-AUC | **0,415** (IC 95 % : 0,410–0,420) | 0,309 | 0,213 |
| ROC-AUC | 0,719 | 0,659 | 0,500 |
| F1 | 0,447 | 0,419 | — |
| Précision | 0,324 | 0,298 | — |
| Rappel | 0,719 | 0,710 | — |

- **AC-05 satisfait** : la PR-AUC dépasse la baseline de 0,106 (soit +34 %), hors de l'intervalle de confiance. La performance est même supérieure à celle de la validation (0,390) ; la prévalence plus élevée du test (21,3 % contre 19,1 %) y contribue, la PR-AUC dépendant de la prévalence.
- **Le gain sur la baseline est réel mais modeste en valeur absolue** : le modèle identifie les retards bien au-dessus du hasard (ROC-AUC 0,72), pas de façon fiable vol par vol. À ce seuil, **environ 2 alertes sur 3 sont de fausses alertes** (précision 0,324) pour un rappel de 0,719.
- **Calibration** : probabilité moyenne prédite 0,225 pour une fréquence observée de 0,213 (surestimation de 1,2 point ; sur la validation c'était une sous-estimation de 1,2 point : la dérive change de sens d'une période à l'autre). Brier 0,149.

### Régression (perte absolue)

| | Modèle | Médiane par aéroport × heure | Médiane globale |
|---|---|---|---|
| MAE (min) | **22,06** (IC 95 % : 21,84–22,31) | 22,17 | 22,31 |
| RMSE (min) | 60,06 | 62,51 | 62,93 |
| Erreur absolue médiane (min) | 7,1 | 5,0 | 5,0 |

- **AC-06 satisfait à la lettre, mais de justesse** : la MAE du modèle est inférieure de **0,11 min (0,5 %)** à la meilleure baseline ; cet écart est **plus petit que l'intervalle de confiance du modèle** (un test apparié n'a pas été fait) et ne doit pas être présenté comme une amélioration établie en MAE. Sur la validation, l'avantage était de 2,5 % : il a presque disparu hors échantillon, ce qui confirme l'optimisme de la validation.
- Le modèle améliore nettement le RMSE (−4 %), donc les gros retards, mais l'erreur absolue **médiane** est plus mauvaise que la baseline (7,1 contre 5,0) : il déplace ses prédictions vers le haut, au prix des vols à l'heure.
- Conclusion honnête : **à T-2h, avec ces variables, la régression des minutes de retard est peu informative** ; la classification est la fonctionnalité utile.

### Erreurs par segment (test)

- **Aéroport** : EWR est surestimé (0,243 prédit, 0,222 observé), JFK surestimé (0,234 contre 0,205), LGA assez bien calibré (0,202 contre 0,211).
- **Heure de départ** : le taux de retard monte de 8 % (6 h–9 h : 9,8 %) à 41 % (22 h–23 h) ; le modèle suit cette tendance (prédit 0,116 → 0,427). L'erreur absolue en minutes croît avec l'heure (11,9 min le matin, 34,1 min en soirée) : **les retards du soir sont les plus difficiles à estimer**.
- **Mois** : janvier est nettement surestimé (0,223 prédit, 0,166 observé), alors que mai–juillet sont bien calibrés (juillet : 0,295 contre 0,295). Les taux historiques sur 28 jours suivent mal la baisse hivernale.
- **Compagnie (8 plus grandes)** : B6 (0,305 prédit, 0,251 observé) et UA (0,256 contre 0,214) sont surestimées ; YX est sous-estimée (0,155 contre 0,179) ; DL et AA sont bien calibrées.

### Limites à afficher (à ne pas minimiser)

- Le test ne couvre que janvier–juillet 2025 (pas de fin d'année) ; un seul été.
- Les probabilités classent les vols mais ne sont pas des fréquences exactes (dérive d'un mois et d'une période à l'autre).
- Météo : dernière observation ≤ T-2h, pas une prévision ; aucune information sur l'avion précédent ni la congestion.
- Résultats rétrospectifs sur données historiques, **pas une prédiction en temps réel**.

## 9. Décision sur la régression (2026-11-14)

À la lecture du §8, le propriétaire a décidé de **reporter le modèle de régression** (il pourra être ajouté plus tard) ([ADR-0017](../05-decisions/adr/0017-regression-postponed.md), D-21) : gain en MAE non établi sur le test, erreur médiane plus mauvaise que la baseline. Les résultats de régression des §2, §3, §5, §6 et §8 sont conservés comme **trace de recherche** ; seuls le modèle de classification, son seuil (0,200) et ses explications SHAP sont des livrables. AC-06 est suspendu.

## 10. Synthèse G3 et cibles de qualité (T4.8) — **approuvées par le propriétaire le 2026-11-14**

### Synthèse des mesures (classification, modèle figé)

| Mesure | Validation | Test (usage unique) | Baseline (test) |
|---|---|---|---|
| PR-AUC | 0,390 | **0,415** (IC 95 % 0,410–0,420) | 0,309 |
| ROC-AUC | 0,720 | 0,719 | 0,659 |
| F1 au seuil 0,200 | 0,429 | 0,447 | 0,419 |
| Précision / rappel | 0,346 / 0,566 | 0,324 / 0,719 | 0,298 / 0,710 |
| Calibration (prédit − observé) | −1,2 pt | +1,2 pt | — |
| Brier | 0,138 | 0,149 | — |

### Verdict G3 (approuvé : go pour la classification) (« les modèles battent-ils la baseline de façon significative ? »)

**Oui pour la classification** : +0,106 de PR-AUC sur le test (+34 %), intervalle de confiance entièrement au-dessus de la baseline, avantage confirmé sur la validation (+0,111). **Non pour la régression** (gain de 0,5 % non établi), déjà reportée (ADR-0017). Réserve à retenir : la valeur absolue reste modeste (ROC-AUC 0,72, environ 2 alertes sur 3 fausses à ce seuil) ; le produit est un **indicateur de risque**, pas une prédiction fiable vol par vol. Le go/no-go est **la décision du propriétaire**.

### Cibles de qualité (D-22, approuvée ; `config.QUALITY_*`, contrôle `models/quality.py`, AC-09)

Un modèle de classification n'est enregistré dans le Model Registry que si, sur le jeu d'évaluation du pipeline, **toutes** les conditions suivantes sont vraies :

| Condition | Seuil proposé | Valeur mesurée (test) | Marge |
|---|---|---|---|
| Gain de PR-AUC sur la baseline aéroport × heure | ≥ +0,05 | +0,106 | ×2 |
| ROC-AUC | ≥ 0,65 | 0,719 | +0,07 |
| Calibration : \|probabilité moyenne prédite − fréquence observée\| | ≤ 0,03 | 0,012 | ×2,5 |
| Tests de non-fuite (colonnes interdites, météo > T-2h, historique) | tous verts | verts | — |

Justification : les seuils sont fixés **sous** les valeurs mesurées (marge de sécurité pour la dérive d'une période à l'autre : la calibration a changé de signe entre validation et test) mais **bien au-dessus** de la baseline et du hasard. Ils sont relatifs à la baseline recalculée sur le même jeu pour ne pas dépendre de la prévalence. À réviser après les premiers réentraînements réels. Les objectifs de latence (D-10 : p95 `/predict` < 3 s, `/stats` < 10 s) restent provisoires et se mesurent en T7.8.

## 11. Artefacts et prédicteur partagé (T4.9)

Commande : `uv run python -m aeropulse.models.release` → `data/ml/release/` (non versionné) : `classifier.json`, `meta.json` (variables, catégories, seuil, paramètres ; sans régression), `manifest.json` (SHA-256, **version `clf-f25ebbd328c5`**, seuil 0,2001). L'empreinte du classifieur est identique à celle enregistrée par l'évaluation finale sur le test : c'est le modèle évalué. Le régresseur n'est pas exporté (ADR-0017).

`aeropulse.models.predict.Predictor` charge l'export et applique **le même code de variables que l'entraînement** (`train.features`) : probabilité, décision au seuil figé, version, explications SHAP (≥ 3 contributions, « influence, pas cause »). **Parité vérifiée sur 20 000 vols de validation : écart maximal 0,0** avec le chemin d'entraînement (risque R-18 couvert côté modèle). Le contrôle de contrat refuse un modèle dont les variables diffèrent de `config.FEATURE_COLUMNS`.

## 12. À venir

WP5 (SageMaker), conditionné à **G0** (approbation de l'estimation de coûts) · construction des variables pour un vol saisi (météo ≤ T-2h et historique) dans le service de prédiction (T7.3) · relecture de non-fuite avant G2 (T0.7).
