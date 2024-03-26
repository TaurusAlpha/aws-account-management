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
