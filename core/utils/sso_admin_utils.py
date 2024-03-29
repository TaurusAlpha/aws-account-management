from collections import namedtuple

from mypy_boto3_identitystore import IdentityStoreClient
from mypy_boto3_sso_admin import SSOAdminClient

from core.authentication.aws_client_factory import AWSClientFactory
from core.schemas.ps_requests import PSConfigPayload

PrincipalDetails = namedtuple("PrincipalDetails", ["principal_type", "principal_id"])
IAMSSOInstance = namedtuple("IAMSSOInstance", ["identity_store_id", "instance_arn"])


def get_iam_sso_instance_data() -> list[IAMSSOInstance]:
    """
    Retrieves the ARNs (Amazon Resource Names) of all SSO instances.

    Returns:
        A list of IAMSSOInstance objects containing the IdentityStoreId and InstanceArn.
    """
    sso_response = AWSClientFactory.get(SSOAdminClient).list_instances()

    return list(
        IAMSSOInstance(
            next(sso_response)["IdentityStoreId"], next(sso_response)["InstanceArn"]
        )
    )


def get_ps_details_for_account(account_id: str) -> dict[str, PSConfigPayload]:
    """
    Retrieves a dictionary of permission sets (PS) for a given account.

    Args:
        account_id (str): The ID of the account.

    Returns:
        dict[str, PSConfigPayload]: A dictionary where the keys are the PS names and the values are PSConfigPayload objects.

    """
    ps_data = {}
    for instance_data in get_iam_sso_instance_data():
        for ps_name, ps_arn in get_ps_name_arn_for_account(
            instance_data.instance_arn, account_id
        ).items():
            principal_details = get_ps_principal_details(
                account_id, instance_data.instance_arn, ps_arn
            )
            ps_data[ps_name] = PSConfigPayload(
                InstanceArn=instance_data.instance_arn,
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


def get_ps_arn_for_name(ps_name: str) -> dict[str, str]:
    """
    Retrieves the ARN (Amazon Resource Name) for a given PS (Permission Set) name.

    Args:
        ps_name (str): The name of the PS to retrieve the ARN for.

    Returns:
        dict[str, str]: A dictionary containing the ARN of the PS, with the PS name as the key.

    """
    instance_data = get_iam_sso_instance_data()
    for _, instance_arn in instance_data:
        ps_list = get_full_ps_list_for_instance(instance_arn)
        ps_name_arn = find_first_matching_ps_name(ps_list, instance_arn, ps_name)
        if ps_name_arn:
            return ps_name_arn

    return {}


def find_first_matching_ps_name(
    ps_list: list[str], instance_arn: str, ps_name: str
) -> dict[str, str]:
    """
    Finds the first matching PS name in the given list of PS ARNs.

    Args:
        ps_list (list[str]): List of PS ARNs to search through.
        instance_arn (str): Instance ARN.
        ps_name (str): Partial or full name of the PS to find.

    Returns:
        dict[str, str]: A dictionary containing the full PS name as the key and the corresponding PS ARN as the value.
        Returns an empty dictionary if no matching PS name is found.
    """
    for ps_arn in ps_list:
        full_ps_name = get_ps_name(instance_arn, ps_arn)
        if ps_name in full_ps_name:
            return {full_ps_name: ps_arn}
    return {}


def get_full_ps_list_for_instance(instance_arn: str) -> list[str]:
    """
    Retrieves the list of all permission sets provisioned to an SSO instance.

    Args:
        instance_arn (str): The ARN of the SSO instance.

    Returns:
        list[str]: A list of permission set names.
    """
    return AWSClientFactory.get(SSOAdminClient).list_permission_sets(
        InstanceArn=instance_arn
    )["PermissionSets"]


def get_group_id_by_name(group_name: str) -> str:
    """
    Retrieves the ID of a group by its name.

    Args:
        group_name (str): The name of the group.

    Returns:
        str: The ID of the group.
    """
    sso_client = AWSClientFactory.get(IdentityStoreClient)
    instance_data = get_iam_sso_instance_data()
    for identity_id, _ in instance_data:
        group_id = sso_client.list_groups(
            IdentityStoreId=identity_id,
            Filters=[{"AttributePath": "DisplayName", "AttributeValue": group_name}],
        )
        if group_id:
            return group_id

    return ""


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
