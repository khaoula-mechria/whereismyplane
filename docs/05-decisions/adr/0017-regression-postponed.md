# ADR-0017 — Régression reportée : classification seule pour l'instant

- **Statut** : **Acceptée le 2026-11-14** (décision du propriétaire : « abandonner la régression pour le moment, mais elle peut être ajoutée »). **Report, pas abandon définitif** : réouverture possible, conditions en fin de document
- **Date** : 2026-11-14
- **Décision liée** : D-21 ([decisions-pending.md](../decisions-pending.md))
- **Modifie** : [ADR-0007](0007-sagemaker-two-endpoints.md) (deux endpoints → un seul), FR-08, FR-09, FR-13, FR-14, AC-06
- **S'appuie sur** : le rapport de modélisation ([model-report.md](../../04-quality/model-report.md), §8)

## Contexte

Le plan initial prévoyait deux modèles : classification (`dep_delay > 15`) et régression (minutes de retard). L'évaluation finale sur le test (T4.6, usage unique, 200 417 vols) a donné :

- **Classification** : PR-AUC 0,415 contre 0,309 pour la baseline (intervalle de confiance 95 % : 0,410–0,420) ; AC-05 satisfait.
- **Régression** : MAE 22,06 min contre 22,17 min pour la meilleure baseline, soit −0,5 %, **à l'intérieur de l'intervalle de confiance du modèle** ; erreur absolue médiane **pire** que la baseline (7,1 contre 5,0 min). AC-06 n'était satisfait qu'à la lettre. Sur la validation, l'avantage était de 2,5 % et a presque disparu hors échantillon.

À T-2h, avec les variables disponibles, une estimation en minutes est trop peu informative pour être présentée à un utilisateur sans l'induire en erreur.

## Décision

**AeroPulse n'embarque, pour le moment, aucun modèle de régression ; son ajout reste possible plus tard.** Le produit prédit la **probabilité de retard de plus de 15 minutes** (classification), avec le seuil choisi sur la validation (ADR-0015) et des explications SHAP. Aucune « durée de retard estimée » n'est affichée ni renvoyée.

Conséquences de périmètre :

- **Un seul modèle, un seul endpoint** SageMaker (temporaire, D-07) au lieu de deux : le coût des endpoints est divisé par deux.
- `POST /predict` ne renvoie plus `expected_delay_minutes` ni de version de modèle de régression.
- Les **statistiques descriptives** (retard moyen par compagnie, aéroport, itinéraire, via `analytics/`) restent disponibles : ce sont des observations historiques, pas des prédictions.
- La colonne `dep_delay` reste dans `ml_dataset` comme valeur observée (base de `is_delayed`, statistiques descriptives) ; elle n'est plus une cible d'apprentissage et reste interdite comme variable (ADR-0003).
- **AC-06 est suspendu** (à rétablir si la régression est ajoutée) ; FR-08 et FR-09 sont réduits à la classification tant que la régression est reportée.

## Alternatives écartées

| Alternative | Raison |
|---|---|
| Garder la régression comme fonctionnalité secondaire dès maintenant | Peu informative (gain de 0,5 % en MAE, non établi) ; risque de présenter une durée trompeuse ; coûte un second endpoint |
| Améliorer la régression avec de nouvelles variables | Reporté ; le jeu de test ayant servi, toute mesure demanderait de nouvelles données ou une validation temporelle |
| Quantiles de retard (« entre X et Y min ») | Hors périmètre ; à reconsidérer si de nouvelles variables (avion précédent, congestion) deviennent disponibles |

## Conséquences

- (+) Produit plus simple, message honnête (un risque, pas une durée), coûts SageMaker réduits, un artefact de moins à maintenir.
- (−) Perte de l'indication de gravité du retard ; la fonctionnalité « minutes estimées » (UC-02) disparaît.
- Le code d'entraînement de la régression (`models/train.py`, `tune.py`, `final.py`) est **conservé** : il facilitera une réouverture, mais n'alimente aucun livrable pour le moment ; le modèle `regressor.json` n'est pas versionné ni déployé.
- Impacts : T4.3 (reportée), T4.4–T4.9, T5.2–T5.6, T7.3, estimation de coûts (un endpoint), AC-06 (retiré).

## Conditions pour rouvrir la décision

La régression pourra être ajoutée (par un nouvel ADR qui remplace celui-ci) si **au moins une** des conditions suivantes est remplie :

1. **De nouvelles variables informatives** deviennent disponibles et sont validées sans fuite (par exemple retard de l'avion précédent, congestion de l'aéroport dans l'heure précédente, prévisions météo archivées).
2. **Un besoin utilisateur précis** apparaît pour une estimation de gravité (par exemple « retard probable > 60 min », ou quantiles), avec un critère de succès chiffré.
3. **De nouvelles données** (période postérieure à juillet 2025) permettent d'évaluer la régression sans réutiliser le jeu de test déjà consommé (T4.6 : usage unique, 2026-11-14).

Éléments à prévoir à la réouverture :

- une **évaluation sur des données jamais vues** (le jeu de test 2025 ne peut plus servir à mesurer une amélioration) ;
- un critère clair **en MAE et en erreur médiane**, et une cible plus parlante que les minutes brutes (par exemple le dépassement d'un seuil de gravité, ou des quantiles) ;
- le rétablissement d'**AC-06**, de **T4.3**, d'un **second endpoint** (ou d'un modèle multi-sorties) et de l'**estimation de coûts** correspondante (environ 0,92 USD/mois nominal, 19,32 USD si l'endpoint est oublié une semaine, d'après [cost-estimate.md](../../04-quality/cost-estimate.md)) ;
- la mise à jour de FR-08, FR-09, FR-13, FR-14, de `/predict` et des diagrammes.
