"""FrontendStack : console de test statique (S3 privé + CloudFront) devant l'API (CMP-16).

Une seule distribution CloudFront sert la page (``/``) et relaie ``/v1/*`` vers API Gateway :
même origine, donc **aucun CORS** à ouvrir (CORS « limité à l'origine CloudFront »). Le bucket
reste privé (Origin Access Control). La clé d'API n'est pas dans la page : l'utilisateur la
saisit (D-05). Politique d'en-têtes stricte (CSP sans script en ligne).

La console de test n'est pas le frontend React prévu (T7.5–T7.7), qui reste à faire.
"""

from __future__ import annotations

from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

from infra.settings import Settings

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


class FrontendStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        settings: Settings,
        api: apigw.RestApi,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        site = s3.Bucket(
            self,
            "SiteBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        headers = cloudfront.ResponseHeadersPolicy(
            self,
            "SecurityHeaders",
            comment="AeroPulse : en-têtes de sécurité",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                content_security_policy=cloudfront.ResponseHeadersContentSecurityPolicy(
                    content_security_policy=CSP, override=True
                ),
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(override=True),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY, override=True
                ),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.NO_REFERRER, override=True
                ),
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=cdk.Duration.days(365),
                    include_subdomains=True,
                    override=True,
                ),
            ),
        )
        distribution = cloudfront.Distribution(
            self,
            "Distribution",
            comment="AeroPulse : console de test + API /v1",
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                response_headers_policy=headers,
            ),
            additional_behaviors={
                "/v1/*": cloudfront.BehaviorOptions(
                    origin=origins.RestApiOrigin(api),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=(
                        cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER
                    ),
                    response_headers_policy=headers,
                )
            },
        )
        s3deploy.BucketDeployment(
            self,
            "DeploySite",
            sources=[s3deploy.Source.asset(str(settings.site_dir))],
            destination_bucket=site,
            distribution=distribution,
            distribution_paths=["/*"],
        )
        cdk.CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        cdk.CfnOutput(self, "DistributionId", value=distribution.distribution_id)
