# Dictionnaire de données

> Statut : **squelette, aucune colonne vérifiée.** Les 33 variables annoncées du dataset ne sont pas connues. Ce fichier est complété en **T1.3** après inspection du fichier réel ([dataset-card.md](dataset-card.md)). Ne rien y ajouter qui ne provienne pas du fichier.

## Mode d'emploi

Une ligne par colonne source. La colonne « Disponible à T-2h » alimente directement la liste des colonnes interdites de `config` ([ADR-0003](05-decisions/adr/0003-t-minus-2h-horizon.md)). Valeurs : **oui** (connu à T-2h), **non** (connu après), **à vérifier**.

## Concepts attendus d'après la synthèse (non vérifiés)

Ce tableau liste des concepts dont la synthèse parle ; leur présence, nom et format réels sont **inconnus**.

| Concept | Rôle prévu | Disponible à T-2h | Statut |
|---|---|---|---|
| Retard au départ (`dep_delay`) | Cible de régression ; base de `is_delayed` | non | Nom et unité à vérifier |
| Heure de départ programmée | Variable, définition de T-2h | oui | À vérifier (fuseau) |
| Heure réelle de départ | **Interdit** | non | À vérifier |
| Heure réelle d'arrivée, retard d'arrivée | **Interdit** | non | À vérifier |
| Compagnie | Variable | oui | À vérifier |
| Aéroport de départ / d'arrivée | Variable, clé | oui | À vérifier |
| Distance | Variable | oui | À vérifier |
| Variables météo (température, vent, visibilité, précipitations, …) | Variables sous condition D-01 | **à vérifier** (dépend de l'horodatage) | Liste réelle inconnue |
| Annulation / déroutement | À décider (inclusion/exclusion) | non | À vérifier |

## Dictionnaire (à remplir en T1.3)

| # | Colonne | Type | Unité | Signification | Valeurs / plage | % manquants | Disponible à T-2h | Rôle (clé, variable, cible, interdit) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | — | — | — | — | — | — | — | — | À compléter |

Critère de complétude (AC-01) : 100 % des colonnes du fichier réel sont décrites.

## Tables dérivées

Les schémas des tables `flights_clean`, `weather_obs`, `ml_dataset` et agrégats sont décrits de façon indicative dans [database-design.md](02-architecture/database-design.md) et seront alignés sur ce dictionnaire une fois rempli.
