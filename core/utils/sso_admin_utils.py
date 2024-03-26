from mypy_boto3_sso_admin import SSOAdminClient

from core.authentication.aws_client_factory import AWSClientFactory


def get_instance_arns() -> list[str]:
    sso_client = AWSClientFactory.get(SSOAdminClient)
    sso_response = sso_client.list_instances()
    return list(map(lambda x: x["InstanceArn"], sso_response["Instances"]))

