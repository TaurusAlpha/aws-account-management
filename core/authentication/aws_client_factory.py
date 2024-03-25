from __future__ import annotations

import os
import re
import typing
from typing import TYPE_CHECKING, Optional, Protocol, Type

import boto3
from botocore.client import BaseClient

if TYPE_CHECKING:
    from mypy_boto3.literals import ServiceName
    from mypy_boto3_sts.type_defs import CredentialsTypeDef


# used to extract client name from a mypy_boto3 module name
ClientNamePattern = re.compile(r"mypy_boto3_(.*?)\.client")
ClientNamePatternMatchGroup = 1


class IAWSClientFactory(Protocol):

    @classmethod
    def get[T](
        cls, client_class: Type[T], region: str = ..., role_arn: Optional[str] = ...
    ) -> T: ...
    """
    Only works in python > 3.12.
    This will provide proper typing to the user regardless of boto3 vscode extension.
    
    Downside:
        This requires the user to create clients using mypy_boto3 types
    """


class AWSClientFactory:
    clients: dict[str, BaseClient] = {}

    @classmethod
    def get[T](
        cls,
        client_class: Type[T],
        region: str = os.environ["AWS_REGION"],
        role_arn: Optional[str] = None,
    ) -> T:
        return cls.clients.get(
            f"{client_class.__name__}_{role_arn}",
            cls.__create_aws_client(client_class, region, role_arn),
        )

    @classmethod
    def __create_aws_client[T](
        cls, client_class: Type[T], region: str, role_arn: Optional[str]
    ) -> T:

        session_creds = cls.__get_sts_credentials(role_arn)
        aws_client: T = boto3.client(
            service_name=cls.__client_type_to_service_name(client_class),
            aws_access_key_id=session_creds["AccessKeyId"],
            aws_secret_access_key=session_creds["SecretAccessKey"],
            aws_session_token=session_creds["SessionToken"],
            region_name=region,
        )

        cls.clients[f"{client_class.__name__}_{role_arn}"] = aws_client

        return aws_client

    @staticmethod
    def __client_type_to_service_name[T](client_class: T) -> ServiceName:
        return (
            ClientNamePattern.match(client_class.__module__)
            .group(ClientNamePatternMatchGroup)
            .replace("_", "-")
        )

    @classmethod
    def __get_sts_credentials(cls, role_arn: Optional[str]) -> CredentialsTypeDef:
        if role_arn is None:
            return typing.cast(CredentialsTypeDef, {k: None for k in ["AccessKeyId", "SecretAccessKey", "SessionToken"]})

        sts_client = boto3.client("sts")
        return sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=f"{cls.__name__}_AssumeRoleSession"
        )["Credentials"]
