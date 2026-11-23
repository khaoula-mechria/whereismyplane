"""Point d'entrée de l'application CDK (ADR-0006, D-03 : Python), environnement ``dev``.

Ordre de déploiement : Data → ML → Backend → Frontend → Monitoring. L'assistant Bedrock
(``infra/stacks/ai_stack.py``) n'est ajouté à l'API que si ``-c bedrock_model_id=...`` est fourni
(ADR-0012 : modèle non choisi). Commandes (depuis la racine du dépôt, voir ``infra/README.md``) :
``npx aws-cdk@2.1147.0 synth -c budget_email=<adresse>`` puis ``deploy --all``.
"""

from __future__ import annotations

import aws_cdk as cdk

from infra.constants import STACK_PREFIX
from infra.settings import TAGS, Settings
from infra.stacks.backend_stack import BackendStack
from infra.stacks.data_stack import DataStack
from infra.stacks.frontend_stack import FrontendStack
from infra.stacks.ml_stack import MLStack
from infra.stacks.monitoring_stack import MonitoringStack


def build_app(app: cdk.App) -> dict[str, cdk.Stack]:
    settings = Settings.from_app(app)
    env = settings.env
    data = DataStack(app, f"{STACK_PREFIX}-Data", env=env)
    ml = MLStack(app, f"{STACK_PREFIX}-ML", settings=settings, data_bucket=data.bucket, env=env)
    backend = BackendStack(
        app, f"{STACK_PREFIX}-Backend", settings=settings, data_bucket=data.bucket, env=env
    )
    frontend = FrontendStack(
        app, f"{STACK_PREFIX}-Frontend", settings=settings, api=backend.api, env=env
    )
    monitoring = MonitoringStack(
        app,
        f"{STACK_PREFIX}-Monitoring",
        settings=settings,
        api=backend.api,
        predict_fn=backend.predict_fn,
        stats_fn=backend.stats_fn,
        chat_fn=backend.chat_fn,
        env=env,
    )
    for key, value in TAGS.items():
        cdk.Tags.of(app).add(key, value)
    return {
        "data": data,
        "ml": ml,
        "backend": backend,
        "frontend": frontend,
        "monitoring": monitoring,
    }


def main() -> None:
    app = cdk.App()
    build_app(app)
    app.synth()


if __name__ == "__main__":
    main()
