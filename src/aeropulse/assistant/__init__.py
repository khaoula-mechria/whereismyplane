"""Assistant Bedrock avec appel d'outils (CMP-12).

Aucun accès SQL libre ; le modèle est un paramètre de configuration (ADR-0012 : non choisi).
Version de test : orchestrateur borné (``orchestrator``), garde-fou contre les chiffres inventés
(``grounding``), prompt système (``prompts``).
"""
