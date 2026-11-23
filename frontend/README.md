# frontend

- [test-console/](test-console/) : **console de test statique** (HTML/JS sans dépendance), déployée par `AeroPulse-Frontend` (S3 privé + CloudFront, même origine que `/v1/*`, CSP stricte). Santé, listes autorisées, prédiction (rejeu et saisie manuelle), statistiques. La clé d'API est saisie par l'utilisateur, jamais intégrée à la page.
- Application React + Vite (D-04) : dashboard, formulaire, chat, avertissements. **Non commencée** (T7.5–T7.7).
