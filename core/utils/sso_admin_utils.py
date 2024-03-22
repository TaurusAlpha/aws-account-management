import boto3


def get_instance_arn() -> list[str]:
    sso_client = boto3.client("sso-admin")
    instance_arns = []

    sso_response = sso_client.list_instances()

    for instance in sso_response["Instances"]:
        instance_arn = instance.get("InstanceArn", None)
        if instance_arn is None:
            raise ValueError
        instance_arns.append(instance_arn)

    return instance_arns