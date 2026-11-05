# Conception de l'API

Statut : conception **[Proposée]** à finaliser en T7.1 (OpenAPI) ; décisions applicables **tranchées** : deux modes de prédiction (D-02), clé d'API et limitation de débit sans comptes (D-05), pas d'historique (D-09), rapports Markdown/JSON (D-13), seuil de 30 vols (D-16) — voir [ADR-0013](../05-decisions/adr/0013-mvp-api-usage-scope.md). Style REST/JSON ; version dans le chemin (`/v1`). **Les valeurs des exemples sont purement illustratives** : aéroports, périodes et codes de compagnie dépendront du dataset vérifié.

## 1. Routes

| Méthode | Chemin | Rôle | Exigence |
|---|---|---|---|
| GET | `/v1/health` | Disponibilité de l'API et des endpoints ML | FR-24 |
| GET | `/v1/stats/summary` | Statistiques globales | FR-15 |
| GET | `/v1/stats/airports/{code}` | Statistiques d'un aéroport | FR-15 |
| GET | `/v1/stats/airlines/{code}` | Statistiques d'une compagnie | FR-15 |
| GET | `/v1/stats/routes/{origin}-{destination}` | Statistiques d'un itinéraire | FR-15 |
| GET | `/v1/meta` | Listes autorisées (compagnies, aéroports, plage de dates) | FR-16, FR-18 |
| POST | `/v1/predict` | Prédiction de retard | FR-14 |
| POST | `/v1/chat` | Question à l'assistant | FR-19 |

Paramètres communs des routes `stats` : `from`, `to` (dates ISO, dans la plage de données), `min_sample` (non modifiable à la baisse sous le seuil du serveur).

## 2. Contrats

### `GET /v1/stats/airlines/{code}?from=2024-03-01&to=2024-03-31`

```json
{
  "airline": "XX",
  "period": {"from": "2024-03-01", "to": "2024-03-31"},
  "n_flights": 4120,
  "delay_rate_15min": 0.18,
  "mean_dep_delay_minutes": 7.2,
  "source": "athena:agg_airline_delay",
  "data_coverage": "<période et aéroports réels du dataset vérifié>"
}
```

Si `n_flights` est inférieur à **30** (D-16) : `200` avec `"insufficient_data": true` et sans indicateurs.

### `POST /v1/predict`

Deux modes d'entrée (D-02, tranchée) :

**Saisie manuelle** (exemple de forme) :

```json
{ "airline": "XX", "origin": "JFK", "destination": "ZZZ",
  "scheduled_departure": "2025-03-14T08:30:00-04:00" }
```

**Rejeu d'un vol de la période de test** : `{ "flight_id": "…" }`.

Dans les deux cas, la météo est la dernière observation historique ≤ T-2h (D-01). Si la reconstruction est impossible pour le dataset ([dataset-card.md](../dataset-card.md)), la route répond `503 weather_unavailable` ou le mode est désactivé ; aucune météo n'est inventée. En saisie manuelle, l'origine doit appartenir à la liste d'aéroports du dataset vérifié (`/v1/meta`).

Sortie : voir l'exemple de [use-cases.md](../01-planning/use-cases.md#uc-02--prédire-un-retard) (champs `delay_probability`, `is_delayed_predicted`, `threshold`, `expected_delay_minutes`, `model_versions`, `explanation`, `disclaimer`).

### `POST /v1/chat`

```json
// requête
{ "session_id": "uuid-optionnel", "message": "Quelle compagnie a le plus de retards à JFK ?" }
// réponse
{ "answer": "…", 
  "sources": [{"tool": "get_airline_delay_statistics", "period": "<période réelle du dataset>"}],
  "tool_calls": 2, "truncated": false }
```

Historique de conversation : géré côté client (envoyé avec la requête), sans base de sessions (D-09). Le modèle Bedrock utilisé est un paramètre de configuration (non choisi, [ADR-0012](../05-decisions/adr/0012-bedrock-model-selection.md)).

### Erreurs (format commun)

```json
{ "error": { "code": "invalid_parameter", "message": "…", "field": "origin", "correlation_id": "…" } }
```

| HTTP | Code | Cas |
|---|---|---|
| 400 | `invalid_parameter` | Valeur hors liste autorisée, date hors plage, format invalide |
| 404 | `not_found` | Entité inconnue |
| 429 | `rate_limited` | Limitation de débit |
| 503 | `model_unavailable` | Endpoint SageMaker arrêté (cas normal hors démonstration) ou indisponible |
| 503 | `weather_unavailable` | Météo à T-2h non reconstructible pour l'entrée demandée |
| 504 | `timeout` | Dépassement de délai |

## 3. Outils de l'assistant

Fonctions Python indépendantes de Bedrock, exposées au LLM avec un schéma d'entrée strict. Les paramètres suivent les mêmes listes autorisées que l'API.

| Outil | Paramètres (extrait) | Source | Sortie |
|---|---|---|---|
| `get_flight_statistics` | `from`, `to` | Athena (agrégats) | indicateurs globaux + échantillon |
| `get_airport_delay_statistics` | `airport`, `from`, `to` | Athena | idem |
| `get_airline_delay_statistics` | `airline`, `airport?`, `from`, `to` | Athena | idem |
| `get_route_delay_statistics` | `origin`, `destination`, `from`, `to` | Athena | idem |
| `predict_flight_delay` | mêmes champs que `/predict` | SageMaker | prédiction |
| `explain_prediction` | résultat de prédiction ou identifiant | SageMaker (SHAP) | contributions |
| `generate_delay_report` | résultats d'outils déjà obtenus | Entrée seule | rapport Markdown/JSON |

Règles communes : validation par liste blanche, `limit` plafonné, aucune chaîne SQL fournie par le LLM, sortie toujours accompagnée de `source`, `period`, `n_flights`. Les entrées issues de la conversation sont traitées comme non fiables (injection).

## 4. Transverse

| Sujet | Proposition |
|---|---|
| Authentification | Pas de compte (D-05, tranchée) ; clé d'API + plans d'utilisation pour limiter le débit. La clé est visible côté client : elle limite l'abus, elle n'authentifie pas un utilisateur |
| CORS | Limité à l'origine CloudFront |
| Limitation de débit | Par clé, plus stricte sur `/chat` et `/predict` (coûts) |
| Idempotence | Toutes les routes sont sûres à rejouer |
| Versionnement | Préfixe `/v1`, changements cassants → `/v2` |
| Documentation | Spécification OpenAPI générée ou écrite à l'étape 7 |
