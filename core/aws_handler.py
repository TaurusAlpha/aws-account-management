from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Callable, Optional

from mypy_boto3_servicecatalog import ServiceCatalogClient
from mypy_boto3_servicecatalog.type_defs import ProvisioningParameterTypeDef

from core.authentication.aws_client_factory import IAWSClientFactory
from core.schemas import SearchProvisionedProductsResponse

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(message)s")
logger.setLevel(logging.INFO if os.getenv("logger_level") else logging.DEBUG)


class AWS:
    def __init__(self, aws_client_factory: IAWSClientFactory):
        self.aws_client_factory = aws_client_factory

    def __block_until_complete(
        self,
        task: Callable,
        args: list[Any],
        condition: Callable[..., bool],
        timeout: float = 5,
    ) -> None:
        """Executes a task repeatedly until a condition is met or a timeout occurs.

        Args:
            task: The callable task to execute.
            args: A list of arguments to pass to the task.
            condition: A callable that takes the task's response and returns a bool.
            timeout: Time to wait between retries (in seconds).

        Raises:
            TimeoutError: If the operation times out.
        """

        start_time = time.time()
        # TODO: Change to global/environment variable
        total_timeout = 30.0

        response = task(*args)
        logger.info(f"Initial request: {response}")

        # TODO: Because AWS API is used, can we proceed after timeout reached?
        while condition(response):
            if time.time() - start_time > total_timeout:
                raise TimeoutError("Operation timed out.")
            time.sleep(timeout)
            response = task(*args)
            logger.info(f"Running request: {response}")

    def __get_sc_products_for_account(self, account_id: str) -> list[str]:
        """
        Retrieves the list of Service Catalog product IDs for a given account.

        Args:
            account_id (str): The ID of the account.

        Returns:
            list[str]: A list of Service Catalog product IDs.

        """
        sc_product_ids = []
        sc_client = self.aws_client_factory.get(ServiceCatalogClient)
        response = sc_client.search_provisioned_products(
            AccessLevelFilter={"Key": "Account", "Value": "self"},
            Filters={"SearchQuery": [account_id]},
        )

        try:
            sc_response = SearchProvisionedProductsResponse(**response)  # type: ignore[call-arg]
        except TypeError:
            return []


        for sc_provisioned_product in sc_response.ProvisionedProducts:
            if sc_provisioned_product.Status == "AVAILABLE":
                sc_product_ids.append(sc_provisioned_product.Id)


        return sc_product_ids

    def deregister_account(self, account_id: str) -> str:
        """
        Deregisters an AWS account from the provisioned Service Catalog.

        Args:
            account_id (str): The ID of the AWS account to deregister.

        Returns:
            str: A message indicating the result of the deregistration process.
        """
        provisioned_products = []
        sc_client = self.aws_client_factory.get(ServiceCatalogClient)
        provisioned_products = self.__get_sc_products_for_account(account_id)

        if provisioned_products is None:
            return f"No provisioned products found for {account_id}"


        for provisioned_product in provisioned_products:
            record_id_response = sc_client.terminate_provisioned_product(  # type: ignore[call-arg]
                ProvisionedProductId=provisioned_product, IgnoreErrors=True
            )

            record_id = record_id_response["RecordDetail"]["RecordId"]

            self.__block_until_complete(
                task=lambda x: sc_client.describe_record(Id=record_id)["RecordDetail"],
                args=[],
                condition=lambda x: x["Status"]
                in ["IN_PROGRESS", "IN_PROGRESS_IN_ERROR", "CREATED"],
            )

        return f"Successfully terminated ControlTower account {account_id} from provisioned Service Catalog ID: {provisioned_products}"

    def get_service_catalog_product_id(self, product_name_keyword: str) -> str:
        """
        Retrieves the ID of a service catalog product based on a keyword.

        Args:
            product_name_keyword (str): The keyword used to search for the product.

        Returns:
            str: The ID of the matching product.

        Raises:
            ValueError: If multiple products are found for the given keyword.
        """

        sc_client = self.aws_client_factory.get(ServiceCatalogClient)
        response = sc_client.search_products_as_admin(
            Filters={"FullTextSearch": [product_name_keyword]}
        )

        matching_products = [
            product.get("ProductViewSummary", {}).get("Id", "")
            for product in response["ProductViewDetails"]
            if product_name_keyword.lower()
            in product.get("ProductViewSummary", {}).get("Name", "").lower()
        ]

        if not matching_products:
            logger.warning(f"No products found for keyword: {product_name_keyword}")
        if len(matching_products) != 1:
            raise ValueError(
                f"Multiple products found for keyword: {product_name_keyword}"
            )

        return matching_products[0]

    def get_product_artifact_id(self, product_id: str) -> str:
        """
        Retrieves the artifact ID for a given product ID.

        Args:
            product_id (str): The ID of the product.

        Returns:
            str: The artifact ID of the product.

        Raises:
            ValueError: If no active artifact is found for the product.
        """
        sc_client = self.aws_client_factory.get(ServiceCatalogClient)
        response = sc_client.describe_product_as_admin(Id=product_id)

        artifact_summary = response["ProvisioningArtifactSummaries"]

        try:
            return next(
                (
                    id
                    for id in map(
                        self.__get_artifact_id_if_current,
                        (
                            (product_id, artifact_id.get("Id", ""))
                            for artifact_id in artifact_summary
                        ),
                    )
                    if id
                )
            )
        except StopIteration:
            raise ValueError(f"No active artifact found for product: {product_id}")

    def __get_artifact_id_if_current(
        self, artifact_and_product_id: tuple[str, str]
    ) -> Optional[str]:
        """
        Retrieves the artifact ID if it is currently active for the given product ID.

        Args:
            artifact_and_product_id: A tuple containing the artifact ID and product ID.

        Returns:
            The artifact ID if it is currently active, otherwise None.
        """
        product_id, artifact_id = artifact_and_product_id
        sc_client = self.aws_client_factory.get(ServiceCatalogClient)
        response = sc_client.describe_provisioning_artifact(
            ProductId=product_id,
            ProvisioningArtifactId=artifact_id,
        )

        return (
            artifact_id
            if response["ProvisioningArtifactDetail"].get("Active", False)
            else None
        )

    def create_control_tower_account(
        self,
        account_name,
        account_email,
        ou_name,
        sso_user_email,
        sso_user_first_name,
        sso_user_last_name,
    ):
        """
        Create a new account in AWS Control Tower via AWS Service Catalog.

        Parameters:
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

        # Replace these with your actual IDs
        # TODO: Hardcoded values should be replaced with environment variables
        product_id = self.get_service_catalog_product_id(
            "AWS Control Tower Account Factory"
        )
        provisioning_artifact_id = self.get_product_artifact_id(product_id)

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

        return response
