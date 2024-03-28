from collections import namedtuple
from typing import NamedTuple
from mypy_boto3_sso_admin import SSOAdminClient

from core.authentication.aws_client_factory import AWSClientFactory


def get_instance_arns() -> list[str]:
    """
    Retrieves the ARNs (Amazon Resource Names) of all SSO instances.

    Returns:
        A list of strings representing the ARNs of all SSO instances.
    """
    sso_client = AWSClientFactory.get(SSOAdminClient)
    sso_response = sso_client.list_instances()
    return list(map(lambda x: x["InstanceArn"], sso_response["Instances"]))


def get_ps_list_for_account(instance_arn, account_id) -> list[str]:
    """
    Retrieves the list of permission sets provisioned to an AWS account.

    Args:
        instance_arn (str): The ARN of the SSO instance.
        account_id (str): The ID of the AWS account.

    Returns:
        list[str]: The list of permission sets provisioned to the account.
    """
    sso_client = AWSClientFactory.get(SSOAdminClient)
    ps_list = sso_client.list_permission_sets_provisioned_to_account(
        InstanceArn=instance_arn, AccountId=account_id
    )["PermissionSets"]

    return ps_list


def provision_ps_for_account(self):
    pass


PrincipalDetails = namedtuple("PrincipalDetails", ["principal_type", "principal_id"])


def get_ps_principal_details(
    account_id: str, instance_arn: str, ps_arn: str
) -> PrincipalDetails:

    sso_admin_client = AWSClientFactory.get(SSOAdminClient)
    sso_response = sso_admin_client.list_account_assignments(
        account_id, instance_arn, ps_arn
    )

    return PrincipalDetails(
        next(sso_response["AccountAssignments"])["PrincipalType"],
        next(sso_response["AccountAssignments"])["PrincipalId"],
    )
