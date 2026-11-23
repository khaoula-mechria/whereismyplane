"""MonitoringStack : AWS Budgets, alarmes CloudWatch, garde-fou des endpoints (CMP-17, T0.6).

- Budget mensuel de 100 USD (D-12b), alertes **réelles** à 50 %, 80 %, 100 % et alerte de
  **prévision** à 100 %, par e-mail. Rappel : un budget notifie, il ne coupe pas les dépenses.
- Alarmes (sujet SNS, e-mail à confirmer) : erreurs des Lambdas, erreurs 5XX de l'API, latence
  p95 de ``/v1/predict`` > 3 s (D-10, provisoire), volume de requêtes anormal.
- Garde-fou quotidien : signale tout endpoint SageMaker actif (aucun n'est attendu).
"""

from __future__ import annotations

from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from constructs import Construct

from infra.constants import PROJECT
from infra.settings import Settings
from infra.stacks.ml_stack import src_code

BUDGET_THRESHOLDS = (50, 80, 100)
PREDICT_P95_MS = 3000  # D-10 (provisoire)
REQUESTS_PER_HOUR_ALARM = 1000


class MonitoringStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        settings: Settings,
        api: apigw.RestApi,
        predict_fn: lambda_.IFunction,
        stats_fn: lambda_.IFunction,
        chat_fn: lambda_.IFunction | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        topic = sns.Topic(self, "Alerts", display_name="AeroPulse alertes", enforce_ssl=True)
        topic.add_subscription(subs.EmailSubscription(settings.budget_email))

        def notification(
            kind: str, pct: int
        ) -> budgets.CfnBudget.NotificationWithSubscribersProperty:
            return budgets.CfnBudget.NotificationWithSubscribersProperty(
                notification=budgets.CfnBudget.NotificationProperty(
                    notification_type=kind,
                    comparison_operator="GREATER_THAN",
                    threshold=pct,
                    threshold_type="PERCENTAGE",
                ),
                subscribers=[
                    budgets.CfnBudget.SubscriberProperty(
                        subscription_type="EMAIL", address=settings.budget_email
                    )
                ],
            )

        budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=f"{PROJECT}-monthly",
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=settings.budget_usd, unit="USD"
                ),
            ),
            notifications_with_subscribers=[
                *(notification("ACTUAL", p) for p in BUDGET_THRESHOLDS),
                notification("FORECASTED", 100),
            ],
        )

        action = cw_actions.SnsAction(topic)
        five_min = cdk.Duration.minutes(5)
        alarms = [
            predict_fn.metric_errors(period=five_min, statistic="Sum").create_alarm(
                self,
                "PredictErrors",
                alarm_description="Erreurs de la Lambda de prédiction",
                threshold=1,
                evaluation_periods=1,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            ),
            stats_fn.metric_errors(period=five_min, statistic="Sum").create_alarm(
                self,
                "StatsErrors",
                alarm_description="Erreurs de la Lambda de statistiques",
                threshold=1,
                evaluation_periods=1,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            ),
            api.metric_server_error(period=five_min, statistic="Sum").create_alarm(
                self,
                "Api5xx",
                alarm_description="Réponses 5XX de l'API",
                threshold=5,
                evaluation_periods=1,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            ),
            predict_fn.metric_duration(period=five_min, statistic="p95").create_alarm(
                self,
                "PredictLatencyP95",
                alarm_description=f"p95 de la prédiction > {PREDICT_P95_MS} ms (D-10)",
                threshold=PREDICT_P95_MS,
                evaluation_periods=3,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            ),
            api.metric_count(period=cdk.Duration.hours(1), statistic="Sum").create_alarm(
                self,
                "ApiVolume",
                alarm_description="Volume de requêtes anormal (protection du budget)",
                threshold=REQUESTS_PER_HOUR_ALARM,
                evaluation_periods=1,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            ),
        ]
        if chat_fn is not None:  # assistant activé (version de test)
            alarms.append(
                chat_fn.metric_errors(period=five_min, statistic="Sum").create_alarm(
                    self,
                    "ChatErrors",
                    alarm_description="Erreurs de la Lambda de l'assistant",
                    threshold=1,
                    evaluation_periods=1,
                    treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
                )
            )
        for alarm in alarms:
            alarm.add_alarm_action(action)

        guard = lambda_.Function(
            self,
            "EndpointGuard",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="aeropulse.mlops.guard.handler",
            code=src_code(settings),
            memory_size=256,
            timeout=cdk.Duration.seconds(60),
            description="Signale tout endpoint SageMaker actif (aucun attendu)",
            environment={"ALERT_TOPIC_ARN": topic.topic_arn},
            log_group=logs.LogGroup(
                self,
                "EndpointGuardLogs",
                retention=logs.RetentionDays.TWO_WEEKS,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            ),
        )
        guard.add_to_role_policy(
            iam.PolicyStatement(actions=["sagemaker:ListEndpoints"], resources=["*"])
        )
        topic.grant_publish(guard)
        events.Rule(
            self,
            "DailyEndpointCheck",
            description="Contrôle quotidien des endpoints SageMaker (07:00 UTC)",
            schedule=events.Schedule.cron(minute="0", hour="7"),
            targets=[targets.LambdaFunction(guard)],
        )

        cdk.CfnOutput(self, "AlertTopicArn", value=topic.topic_arn)
