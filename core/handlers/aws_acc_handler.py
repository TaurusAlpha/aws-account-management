from __future__ import annotations

import json
import uuid

from mypy_boto3_servicecatalog import ServiceCatalogClient
from mypy_boto3_servicecatalog.type_defs import (
    ProvisioningParameterTypeDef,
    ProvisionProductOutputTypeDef,
)
from mypy_boto3_sso_admin import SSOAdminClient

import core.utils as utils
import core.utils.sc_utils as sc_utils
import core.utils.sso_admin_utils as sso_admin_utils
from core.authentication.aws_client_factory import IAWSClientFactory
from core.schemas.handler_response import (
    AWSHandlerResponse,
    OperationStatus,
    OperationType,
)
from core.schemas.ps_requests import PSConfigPayload
from core.utils import logger


class AWS:
    def __init__(self, aws_client_factory: IAWSClientFactory):
        self.aws_client_factory = aws_client_factory

    def terminate_control_tower_account(
        self, account_id: str
    ) -> AWSHandlerResponse | str:
        """
        Deregisters an AWS account from the provisioned Service Catalog.

        Args:
            account_id (str): The ID of the AWS account to deregister.

        Returns:
            str: A message indicating the result of the deregistration process.
        """
        provisioned_products = []
        sc_client = self.aws_client_factory.get(ServiceCatalogClient)
        provisioned_products = sc_utils.get_sc_products_for_account(account_id)

        if provisioned_products is None:
            logger.info(f"No provisioned products found for {account_id}")
            return

        for provisioned_product in provisioned_products:
            record_id_response = sc_client.terminate_provisioned_product(  # type: ignore[call-arg]
                ProvisionedProductId=provisioned_product, IgnoreErrors=True
            )

            record_id = record_id_response["RecordDetail"]["RecordId"]

            utils.block_until_complete(
                task=sc_client.describe_record,
                args=[],
                kwargs={"Id": record_id},
                condition=lambda x: x["RecordDetail"]["Status"]
                in ["IN_PROGRESS", "IN_PROGRESS_IN_ERROR", "CREATED"],
            )

        return f"Successfully terminated ControlTower account {account_id} from provisioned Service Catalog ID: {provisioned_products}"

    def create_control_tower_account(
        self,
        account_name: str,
        account_email: str,
        ou_name: str,
        sso_user_email: str,
        sso_user_first_name: str,
        sso_user_last_name: str,
    ) -> ProvisionProductOutputTypeDef:
        """
        Create a new account in AWS Control Tower via AWS Service Catalog.

        Args:
        - account_name: The name of the new account.
        - account_email: The email address associated with the new account.
        - ou_name: The name of the organizational unit to place the new account in.
        - sso_user_email: The email address for the SSO user in the new account.
        - sso_user_first_name: The first name of the SSO user.
        - sso_user_last_name: The last name of the SSO user.

        Returns:
        - response: The response from the provisioning of the new account.

        """
        sc_client = self.aws_client_factory.get(ServiceCatalogClient)
        account_request_id = str(uuid.uuid4())

        product_id = sc_utils.get_service_catalog_product_id(
            "AWS Control Tower Account Factory"
        )
        provisioning_artifact_id = sc_utils.get_product_artifact_id(product_id)

        # Provisioning parameters for the account creation
        provisioning_parameters: list[ProvisioningParameterTypeDef] = [
            {"Key": "AccountName", "Value": account_name},
            {"Key": "AccountEmail", "Value": account_email},
            {"Key": "ManagedOrganizatialUnit", "Value": ou_name},
            {"Key": "SSOUserEmail", "Value": sso_user_email},
            {"Key": "SSOUserFirstName", "Value": sso_user_first_name},
            {"Key": "SSOUserLastName", "Value": sso_user_last_name},
        ]

        # Provision the new account
        response = sc_client.provision_product(
            ProductId=product_id,
            ProvisioningArtifactId=provisioning_artifact_id,
            ProvisionedProductName=f"AccountCreation-{account_request_id}",
            ProvisioningParameters=provisioning_parameters,
            ProvisionToken=account_request_id,
        )

        record_id = response["RecordDetail"]["RecordId"]

        task_response = utils.block_until_complete(
            task=sc_client.describe_record,
            args=[],
            kwargs={"Id": record_id},
            condition=lambda x: x["RecordDetail"]["Status"]
            in ["IN_PROGRESS", "IN_PROGRESS_IN_ERROR", "CREATED"],
        )

        op_status = OperationStatus.from_str(task_response["RecordDetail"]["Status"])

        return AWSHandlerResponse(
            operation_command=self.create_control_tower_account.__name__,
            operation_status=op_status,
            operation_type=OperationType.CREATE,
            service_name="AWS Control Tower",
            response_payload=task_response,
            message=f"Account creation request for {account_name} has been submitted.",
        )

    def add_account_to_ps(
        self, account_id: str, ps_name: str, group_name: str
    ) -> dict[str, PSConfigPayload]:
        """
        Adds an account to a permission set in the IAM SSO instance.

        Args:
            account_id (str): The ID of the account to be added.
            ps_name (str): The name of the permission set.
            group_name (str): The name of the group.

        Returns:
            dict[str, PSConfigPayload]: A dictionary containing permission set name and the created permission set configuration payload.

        Raises:
            None

        """
        instance_data = sso_admin_utils.get_iam_sso_instance_data()

        for _, instance_arn in instance_data:
            ps_data = sso_admin_utils.get_ps_arn_for_name(ps_name)
            if ps_data is None:
                logger.info(f"Permission set {ps_name} not found in instance")
                return {}
            group_id = sso_admin_utils.get_group_id_by_name(group_name)
            if group_id is None:
                logger.info(f"Group {group_name} not found in instance")
                return {}
            ps_payload = PSConfigPayload(
                InstanceArn=instance_arn,
                TargetId=account_id,
                PermissionSetArn=ps_data["PermissionSetArn"],
                PrincipalType="GROUP",
                PrincipalId=group_id,
            )

            sso_client = self.aws_client_factory.get(SSOAdminClient)
            ps_response = sso_client.create_account_assignment(**ps_payload)[
                "AccountAssignmentCreationStatus"
            ]
            logger.info(
                f"Creation status {ps_response['Status']} for {ps_name} permission set"
            )

            ps_create_status = utils.block_until_complete(
                task=sso_client.describe_account_assignment_creation_status,
                args=[],
                kwargs={
                    "InstanceArn": ps_payload.InstanceArn,
                    "AccountAssignmentCreationRequestId": ps_response["RequestId"],
                },
                condition=lambda x: x["AccountAssignmentCreationStatus"]["Status"]
                in ["IN_PROGRESS"],
            )
            if ps_create_status["Status"] == "FAILED":
                logger.info(
                    f"Create failed for {ps_name}. Fail status message: {ps_create_status['FailureReason']}"
                )

            ps_create_data = {ps_name: ps_payload}

        return ps_create_data

    def remove_account_from_ps(self, account_id: str) -> dict[str, PSConfigPayload]:
        account_id = account_id
        sso_client = self.aws_client_factory.get(SSOAdminClient)
        ps_list_payload = sso_admin_utils.get_ps_details_for_account(account_id)

        for ps_name, ps_payload in ps_list_payload.items():
            ps_delete_status = sso_client.delete_account_assignment(**ps_payload)[
                "AccountAssignmentDeletionStatus"
            ]
            logger.info(
                f"Deletion status {ps_delete_status['Status']} for {ps_name} permission set"
            )

            ps_delete_status = utils.block_until_complete(
                task=sso_client.describe_account_assignment_deletion_status,
                args=[],
                kwargs={
                    "InstanceArn": ps_payload.InstanceArn,
                    "AccountAssignmentDeletionRequestId": ps_delete_status["RequestId"],
                },
                condition=lambda x: x["AccountAssignmentDeletionStatus"]["Status"]
                in ["IN_PROGRESS"],
            )

            if ps_delete_status["Status"] == "FAILED":
                logger.info(
                    f"Delete failed for {ps_name}. Fail status message: {ps_delete_status['FailureReason']}"
                )

        logger.info(f"Permission sets deleted: {json.dumps(ps_list_payload, indent=2)}")
        return ps_list_payload
