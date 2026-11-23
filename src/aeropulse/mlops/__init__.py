"""Chaîne MLOps sur AWS : paquet de service versionné, jobs SageMaker, promotion (ADR-0018).

Les modules ``bundle``, ``store``, ``promote`` et ``guard`` n'utilisent que la bibliothèque
standard (et boto3, fourni par le runtime Lambda) : ils tournent dans une Lambda en archive zip,
sans pandas. Les ``*_job`` tournent dans l'image d'exécution (SageMaker Processing / Training).
"""
