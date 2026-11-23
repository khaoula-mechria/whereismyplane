"""Job Glue PySpark de nettoyage (CMP-02) : **non utilisé** dans le déploiement de test.

La préparation tourne dans l'étape SageMaker Processing ``Prepare``
(``aeropulse.mlops.prepare_job``), qui réutilise le code local testé (ADR-0018, proposée).
Fichier conservé comme emplacement si un job Glue redevient nécessaire (volumes plus grands).
"""
