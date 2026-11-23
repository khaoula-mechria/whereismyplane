# Image d'exécution unique AeroPulse (ADR-0018) : Lambda /v1/predict, /v1/health, /v1/meta,
# /v1/stats/* ET jobs SageMaker (Processing « Prepare »/« Evaluate », Training « Train »).
# Même code de variables à l'entraînement et au service (R-18).
# Contexte de build produit par `uv run python scripts/build_lambda_context.py` (code, dépendances
# verrouillées sans nvidia-*, tests de non-fuite). Le modèle et les tables ne sont PAS dans
# l'image : ils sont lus dans S3 (bundle versionné, vérifié par empreinte).
FROM public.ecr.aws/lambda/python:3.13

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY aeropulse ${LAMBDA_TASK_ROOT}/aeropulse
COPY checks ${LAMBDA_TASK_ROOT}/checks
COPY entrypoint.sh /usr/local/bin/aeropulse-entrypoint.sh
# Fins de ligne Unix même si le dépôt a été extrait sous Windows (CRLF).
RUN sed -i 's/\r$//' /usr/local/bin/aeropulse-entrypoint.sh \
    && chmod 755 /usr/local/bin/aeropulse-entrypoint.sh

ENV PYTHONPATH=${LAMBDA_TASK_ROOT} \
    HOME=/tmp \
    AEROPULSE_CHECKS_DIR=${LAMBDA_TASK_ROOT}/checks

ENTRYPOINT ["/usr/local/bin/aeropulse-entrypoint.sh"]
CMD ["aeropulse.api.predict_handler.handler"]
