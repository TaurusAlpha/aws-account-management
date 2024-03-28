# mypy: disable-error-code="valid-type, name-defined"
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
    def get[
        T
    ](
        cls, client_class: Type[T], region: str = ..., role_arn: Optional[str] = ...
    ) -> T:
        """
        Returns an instance of the specified AWS client class.

        Args:
            client_class (Type[T]): The class of the AWS client to create.
            region (str, optional): The AWS region to use. Defaults to ... (provide default value).
            role_arn (str, optional): The ARN of the role to assume. Defaults to None.

        Returns:
            T: An instance of the specified AWS client class.

        Note:
            Only works in python > 3.12.
            This will provide proper typing to the user regardless of boto3 vscode extension.

            Downside:
                This requires the user to create clients using mypy_boto3 types
        """
        ...


class AWSClientFactory:
    clients: dict[str, BaseClient] = {}

    @classmethod
    def get[
        T
    ](
        cls,
        client_class: Type[T],
        region: str = os.environ["AWS_REGION"],
        role_arn: Optional[str] = None,
    ) -> T:
        """
        Get an AWS client instance.

        Args:
            client_class (Type[T]): The class of the AWS client to create.
            region (str, optional): The AWS region to use. Defaults to the value of the AWS_REGION environment variable.
            role_arn (str, optional): The ARN of the IAM role to assume. Defaults to None.

        Returns:
            T: An instance of the AWS client.

        """
        return cls.clients.get(
            f"{client_class.__name__}_{role_arn}",
            cls.__create_aws_client(client_class, region, role_arn),
        )

    @classmethod
    def __create_aws_client[
        T
    ](cls, client_class: Type[T], region: str, role_arn: Optional[str]) -> T:
        """
        Create an AWS client of the specified type.

        Args:
            client_class (Type[T]): The type of AWS client to create.
            region (str): The AWS region to use.
            role_arn (Optional[str]): The ARN of the IAM role to assume (optional).

        Returns:
            T: The created AWS client.

        """
        session_creds = cls.__get_sts_credentials(role_arn)
        aws_client: T = boto3.client(
            service_name=cls.__client_type_to_service_name(client_class),  # type: ignore
            aws_access_key_id=session_creds["AccessKeyId"],
            aws_secret_access_key=session_creds["SecretAccessKey"],
            aws_session_token=session_creds["SessionToken"],
            region_name=region,
        )

        cls.clients[f"{client_class.__name__}_{role_arn}"] = aws_client

        return aws_client

    @staticmethod
    def __client_type_to_service_name[T](client_class: T) -> ServiceName:  # type: ignore[valid-type, name-defined]
        """
        Converts the client type to a service name.

        Args:
            client_class (Type): The client class.

        Returns:
            ServiceName: The converted service name.
        """
        return (
            ClientNamePattern.match(client_class.__module__)  # type: ignore[union-attr]
            .group(ClientNamePatternMatchGroup)
            .replace("_", "-")
        )

    @classmethod
    def __get_sts_credentials(cls, role_arn: Optional[str]) -> CredentialsTypeDef:
        """
        Get STS credentials for the specified role ARN.

        Args:
            role_arn (Optional[str]): The ARN of the role to assume.

        Returns:
            CredentialsTypeDef: The STS credentials.

        If `role_arn` is None, returns a dictionary with `AccessKeyId`, `SecretAccessKey`,
        and `SessionToken` set to None.

        """
        if role_arn is None:
            return typing.cast(
                CredentialsTypeDef,
                {k: None for k in ["AccessKeyId", "SecretAccessKey", "SessionToken"]},
            )

        sts_client = boto3.client("sts")
        return sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName=f"{cls.__name__}_AssumeRoleSession"
        )["Credentials"]
