# Image Lambda de la route POST /v1/predict (option A : image conteneur, décision du 2026-11-14).
# Le contexte de build est produit par `uv run python scripts/build_lambda_context.py`
# (code, dépendances verrouillées sans nvidia-*, tables de service, modèle vérifié par empreinte).
# Base AWS officielle Lambda Python 3.13 : disponibilité du tag à vérifier au premier build.
FROM public.ecr.aws/lambda/python:3.13

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY aeropulse ${LAMBDA_TASK_ROOT}/aeropulse
COPY serving ${LAMBDA_TASK_ROOT}/serving
COPY release ${LAMBDA_TASK_ROOT}/release

ENV AEROPULSE_SERVING_DIR=${LAMBDA_TASK_ROOT}/serving \
    AEROPULSE_RELEASE_DIR=${LAMBDA_TASK_ROOT}/release

CMD ["aeropulse.api.predict_handler.handler"]
