from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Protocol, overload
import boto3
import os
from botocore.client import BaseClient

if TYPE_CHECKING:
    from mypy_boto3.literals import ServiceName
    from mypy_boto3_cloudformation import CloudFormationClient
    from mypy_boto3_cloudformation.literals import CloudFormationServiceName
    from mypy_boto3_organizations import OrganizationsClient
    from mypy_boto3_organizations.literals import OrganizationsServiceName
    from mypy_boto3_sns import SNSClient
    from mypy_boto3_sns.literals import SNSServiceName
    from mypy_boto3_sts import STSClient
    from mypy_boto3_sts.literals import STSServiceName
    from mypy_boto3_sts.type_defs import CredentialsTypeDef
    from mypy_boto3_servicecatalog import ServiceCatalogClient
    from mypy_boto3_servicecatalog.literals import ServiceCatalogServiceName
    from mypy_boto3_sso_admin import SSOAdminClient
    from mypy_boto3_sso_admin.literals import SSOAdminServiceName


class IAWSClientFactory(Protocol):

    @classmethod
    @overload
    def get_aws_client(
        cls,
        name: SNSServiceName,
        region: Optional[str] = None,
        assume_role: Optional[str] = None,
    ) -> SNSClient: ...

    @classmethod
    @overload
    def get_aws_client(
        cls,
        name: CloudFormationServiceName,
        region: Optional[str] = None,
        assume_role: Optional[str] = None,
    ) -> CloudFormationClient: ...

    @classmethod
    @overload
    def get_aws_client(
        cls,
        name: STSServiceName,
        region: Optional[str] = None,
        assume_role: Optional[str] = None,
    ) -> STSClient: ...

    @classmethod
    @overload
    def get_aws_client(
        cls,
        name: ServiceCatalogServiceName,
        region: Optional[str] = None,
        assume_role: Optional[str] = None,
    ) -> ServiceCatalogClient: ...

    @classmethod
    @overload
    def get_aws_client(
        cls,
        name: OrganizationsServiceName,
        region: Optional[str] = None,
        assume_role: Optional[str] = None,
    ) -> OrganizationsClient: ...

    @classmethod
    @overload
    def get_aws_client(
        cls,
        name: SSOAdminServiceName,
        region: Optional[str] = None,
        assume_role: Optional[str] = None,
    ) -> SSOAdminClient: ...

    @classmethod
    def get_aws_client(
        cls,
        name: ServiceName,
        region: Optional[str] = None,
        assume_role: Optional[str] = None,
    ) -> BaseClient: ...


class AWSClientFactory:
    clients: dict[str, BaseClient] = {}

    @classmethod
    def get_aws_client(
        cls,
        name: ServiceName,
        region: Optional[str] = None,
        assume_role: Optional[str] = None,
    ) -> BaseClient:

        region = region or os.environ["AWS_REGION"]
        client = cls.clients.get(
            f"{name}{assume_role}", cls.__create_aws_client(name, region, assume_role)
        )
        return client

    @classmethod
    def __create_aws_client(
        cls, name: ServiceName, region: str, assume_role: Optional[str]
    ) -> BaseClient:

        session_creds = cls.__get_sts_credentials(assume_role)
        aws_client = boto3.client(
            service_name=name,  # type: ignore
            aws_access_key_id=session_creds["AccessKeyId"],
            aws_secret_access_key=session_creds["SecretAccessKey"],
            aws_session_token=session_creds["SessionToken"],
            region_name=region,
        )

        cls.clients[f"{name}{assume_role}"] = aws_client

        return aws_client

    @classmethod
    def __get_sts_credentials(
        cls, role_arn: Optional[str]
    ) -> CredentialsTypeDef | dict[str, None]:
        if role_arn is None:
            return {k: None for k in ["AccessKeyId", "SecretAccessKey", "SessionToken"]}
        sts_client = boto3.client("sts")
        return sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName="AssumeRoleSession"
        )["Credentials"]
