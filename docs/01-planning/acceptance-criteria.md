# Critères d'acceptation

Format : chaque critère est vérifiable (test automatique ou contrôle manuel défini). Les seuils marqués **(provisoire)** sont ceux de D-10, à confirmer après mesures. Les cibles de performance des modèles sont volontairement relatives à la baseline tant que l'étape 4 n'a pas fourni de référence (T4.8). Le seuil minimal de 30 vols (AC-13) est tranché (D-16).

| ID | Exigences | Critère d'acceptation | Vérification |
|---|---|---|---|
| AC-01 | FR-01, FR-05 | Le nombre de lignes de la zone raw est identique à celui du fichier source ; le dictionnaire de données couvre 100 % des colonnes | Test + revue |
| AC-02 | FR-02, NFR-08 | Après nettoyage : 0 doublon sur la clé d'un vol, 0 date invalide, colonnes critiques sans valeur manquante non traitée ; rapport de validation produit | Test de validation |
| AC-03 | FR-06, FR-07 | Aucune colonne de la liste interdite (heure réelle de départ, retard réel, informations d'arrivée, météo postérieure à T-2h) n'est dans les variables ; le test de non-fuite échoue si on en ajoute une | Test automatique |
| AC-04 | FR-07 | Toute statistique historique d'un vol est calculée uniquement avec des vols dont l'heure de départ est antérieure à T-2h de ce vol | Test sur cas construits |
| AC-05 | FR-08, FR-09 | Le meilleur modèle de classification dépasse la baseline sur PR-AUC (jeu de test chronologique) ; cible chiffrée fixée après l'étape 4 | Rapport d'évaluation |
| AC-06 | FR-08, FR-09 | Le meilleur modèle de régression bat la baseline (moyenne/médiane) en MAE sur le jeu de test ; cible chiffrée fixée après l'étape 4 | Rapport d'évaluation |
| AC-07 | FR-10 | Le seuil de décision est choisi sur la validation et documenté ; le jeu de test n'est utilisé qu'une fois pour l'évaluation finale | Revue du notebook/rapport |
| AC-08 | FR-11 | Une prédiction renvoie au moins 3 contributions SHAP ; le texte de l'interface indique « influence, pas cause » | Test API + contrôle visuel |
| AC-09 | FR-12 | Un modèle n'est enregistré que si ses métriques passent le contrôle de qualité ; version et métriques consultables dans le registry | Exécution du pipeline |
| AC-10 | FR-13, FR-14 | `POST /predict` valide renvoie 200 avec probabilité, minutes, explications, versions de modèles ; entrée invalide renvoie 400 | Tests d'intégration |
| AC-11 | NFR-05 | Latence p95 de `/predict` < 3 s et de `/stats` < 10 s, hors démarrage à froid (provisoire, D-10) | Mesure CloudWatch |
| AC-12 | NFR-02 | `cdk deploy` suivi de `cdk destroy` fonctionne sur un compte vierge sans étape manuelle (hors accès Bedrock) | Exécution documentée |
| AC-13 | FR-15, FR-04, IR-01 | Une statistique pour un échantillon < seuil minimal (tranché : 30 vols, D-16) renvoie « données insuffisantes » | Test |
| AC-14 | FR-21, NFR-06 | Sur le jeu d'évaluation de l'assistant : 100 % des chiffres cités se retrouvent dans la sortie d'un outil ; 0 requête SQL libre exécutée | Jeu d'évaluation |
| AC-15 | FR-20 | Les outils rejettent tout filtre non autorisé, tout dépassement de limite, toute tentative d'injection dans un paramètre | Tests unitaires |
| AC-16 | FR-19 | Sur un jeu de questions étiqueté (≥ 20), l'outil attendu est choisi dans ≥ 85 % des cas (proposé) | Jeu d'évaluation |
| AC-17 | FR-22 | Un rapport ne contient aucun chiffre absent de ses données d'entrée | Test |
| AC-18 | NFR-04 | AWS Budgets de 100 USD/mois configuré avec alertes à 50 %, 80 % et 100 % ; après chaque démonstration, aucun endpoint SageMaker actif (checklist de [cost-estimate.md](../04-quality/cost-estimate.md) exécutée et consignée) | Contrôle de la liste des ressources |
| AC-19 | NFR-03 | Aucun secret dans le dépôt (scan en CI) ; chaque rôle IAM Lambda limité aux ressources utilisées | Scan + revue |
| AC-20 | FR-24, NFR-11 | Chaque requête produit un journal avec identifiant de corrélation, sans données personnelles | Contrôle des logs |
| AC-21 | FR-18 | L'interface (en français) affiche la période réelle, les aéroports réellement couverts et l'avertissement sur les prédictions | Contrôle visuel |
| AC-22 | FR-23 | (Optionnel) Une question documentaire renvoie une réponse avec le passage source ; une question analytique n'utilise pas le RAG | Jeu d'évaluation |
| AC-23 | FR-26 | Source exacte, version et licence du dataset consignées dans `dataset-card.md` ; chaque caractéristique annoncée est marquée vérifiée ou écartée avec la valeur réelle | Revue du document |
| AC-24 | FR-27 | Un rapport de faisabilité établit si, pour chaque vol, la dernière observation météo ≤ T-2h est retrouvable (taux de couverture et âge maximal mesurés) ; en cas d'échec, blocage signalé et aucune donnée artificielle | Rapport (T1.5) |
| AC-25 | NFR-04 | L'estimation de coûts de `cost-estimate.md` est complétée à partir des tarifs officiels `us-east-1`, scénario pessimiste inclus, comparée à 100 USD/mois et approuvée avant le premier déploiement payant | Revue du document (G0) |

## Traçabilité inverse

Chaque FR/NFR de [requirements.md](requirements.md) est couvert : FR-03 par AC-01/AC-02 (lecture via Athena testée en T6.3), FR-16/FR-17 par AC-21 et les tests de bout en bout ([testing-strategy.md](../04-quality/testing-strategy.md)), FR-25 non couvert car optionnel.

## Définition de « terminé » commune à toute étape

1. Critères d'acceptation de l'étape vérifiés.
2. Tests associés passants en CI.
3. Documentation et [PROGRESS.md](../PROGRESS.md) mis à jour.
4. Aucune ressource AWS inutile laissée active.
