from typing import Optional

from mypy_boto3_servicecatalog import ServiceCatalogClient

from core.authentication.aws_client_factory import AWSClientFactory
from core.schemas import SearchProvisionedProductsResponse
from core.utils import logger


# TODO: Review function code
def get_sc_products_for_account(account_id: str) -> list[str]:
    """
    Retrieves the list of Service Catalog product IDs for a given account.

    Args:
        account_id (str): The ID of the account.

    Returns:
        list[str]: A list of Service Catalog product IDs.

    """
    sc_product_ids = []
    sc_client = AWSClientFactory.get(ServiceCatalogClient)
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


def get_artifact_id_if_current(
    artifact_and_product_id: tuple[str, str]
) -> Optional[str]:
    """
    Retrieves the artifact ID if it is currently active for the given product ID.

    Args:
        - artifact_and_product_id: A tuple containing the artifact ID and product ID.

    Returns:
        The artifact ID if it is currently active, otherwise None.
    """
    product_id, artifact_id = artifact_and_product_id
    sc_client = AWSClientFactory.get(ServiceCatalogClient)
    response = sc_client.describe_provisioning_artifact(
        ProductId=product_id,
        ProvisioningArtifactId=artifact_id,
    )

    return (
        artifact_id
        if response["ProvisioningArtifactDetail"].get("Active", False)
        else None
    )


def get_product_artifact_id(product_id: str) -> str:
    """
    Retrieves the artifact ID for a given product ID.

    Args:
        product_id (str): The ID of the product.

    Returns:
        str: The artifact ID of the product.

    Raises:
        ValueError: If no active artifact is found for the product.
    """
    sc_client = AWSClientFactory.get(ServiceCatalogClient)
    response = sc_client.describe_product_as_admin(Id=product_id)

    artifact_summary = response["ProvisioningArtifactSummaries"]

    try:
        return next(
            (
                id
                for id in map(
                    get_artifact_id_if_current,
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


def get_service_catalog_product_id(product_name_keyword: str) -> str:
    """
    Retrieves the ID of a service catalog product based on a keyword.

    Args:
        product_name_keyword (str): The keyword used to search for the product.

    Returns:
        str: The ID of the matching product.

    Raises:
        ValueError: If multiple products are found for the given keyword.
    """

    sc_client = AWSClientFactory.get(ServiceCatalogClient)
    response = sc_client.search_products_as_admin(
        Filters={"FullTextSearch": [product_name_keyword]}
    )
    # logger.info(response)
    matching_products = [
        product.get("ProductViewSummary", {}).get("ProductId", "")
        for product in response["ProductViewDetails"]
        if product_name_keyword.lower()
        in product.get("ProductViewSummary", {}).get("Name", "").lower()
    ]

    if not matching_products:
        logger.warning(f"No products found for keyword: {product_name_keyword}")
    if len(matching_products) != 1:
        raise ValueError(f"Multiple products found for keyword: {product_name_keyword}")

    return matching_products[0]
