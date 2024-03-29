from collections import namedtuple
from mypy_boto3_sso_admin import SSOAdminClient

from core.authentication.aws_client_factory import AWSClientFactory
from core.schemas.ps_requests import PSConfigPayload


PrincipalDetails = namedtuple("PrincipalDetails", ["principal_type", "principal_id"])


def get_instance_arns() -> list[str]:
    """
    Retrieves the ARNs (Amazon Resource Names) of all SSO instances.

    Returns:
        A list of strings representing the ARNs of all SSO instances.
    """
    sso_client = AWSClientFactory.get(SSOAdminClient)
    sso_response = sso_client.list_instances()
    return list(map(lambda x: x["InstanceArn"], sso_response["Instances"]))


def get_ps_list_for_account(account_id: str) -> dict[str, PSConfigPayload]:
    """
    Retrieves a dictionary of permission sets (PS) for a given account.

    Args:
        account_id (str): The ID of the account.

    Returns:
        dict[str, PSConfigPayload]: A dictionary where the keys are the PS names and the values are PSConfigPayload objects.

    """
    ps_data = {}
    for instance_arn in get_instance_arns():
        for ps_name, ps_arn in get_ps_name_arn_for_account(
            instance_arn, account_id
        ).items():
            principal_details = get_ps_principal_details(
                account_id, instance_arn, ps_arn
            )
            ps_data[ps_name] = PSConfigPayload(
                InstanceArn=instance_arn,
                TargetId=account_id,
                PermissionSetArn=ps_arn,
                PrincipalType=principal_details.principal_type,
                PrincipalId=principal_details.principal_id,
            )

    return ps_data


def get_ps_name_arn_for_account(instance_arn, account_id) -> dict[str, str]:
    """
    Retrieves the list of permission sets provisioned to an AWS account.

    Args:
        instance_arn (str): The ARN of the SSO instance.
        account_id (str): The ID of the AWS account.

    Returns:
        dict[str, str]: A dictionary mapping permission set names to their ARNs.
    """
    sso_client = AWSClientFactory.get(SSOAdminClient)
    ps_list = sso_client.list_permission_sets_provisioned_to_account(
        InstanceArn=instance_arn, AccountId=account_id
    )["PermissionSets"]

    # TODO: ask Dude about ps_arn handling in comprehension
    ps_list = {get_ps_name(instance_arn, ps_arn): ps_arn for ps_arn in ps_list}
    return ps_list


def get_ps_name(instance_arn, ps_arn) -> str:
    """
    Retrieves the name of a permission set.

    Args:
        instance_arn (str): The ARN of the SSO instance.
        ps_arn (str): The ARN of the permission set.

    Returns:
        str: The name of the permission set.
    """
    sso_client = AWSClientFactory.get(SSOAdminClient)
    ps_name = sso_client.describe_permission_set(
        InstanceArn=instance_arn, PermissionSetArn=ps_arn
    )["PermissionSet"]["Name"]

    return ps_name


def provision_ps_for_account(self):
    pass


def get_ps_principal_details(
    account_id: str, instance_arn: str, ps_arn: str
) -> PrincipalDetails:
    """
    Retrieves the principal details for a given account, instance, and permission set.

    Args:
        account_id (str): The ID of the AWS account.
        instance_arn (str): The ARN of the AWS SSO instance.
        ps_arn (str): The ARN of the permission set.

    Returns:
        PrincipalDetails: An object containing the principal type and ID.

    """
    sso_admin_client = AWSClientFactory.get(SSOAdminClient)
    sso_response = sso_admin_client.list_account_assignments(
        account_id, instance_arn, ps_arn
    )

    return PrincipalDetails(
        next(sso_response["AccountAssignments"])["PrincipalType"],
        next(sso_response["AccountAssignments"])["PrincipalId"],
    )
