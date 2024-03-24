from typing import Any, Callable
import logging
import os
import time
from core.authentication.aws_client_factory import IAWSClientFactory
from core.schemas import SearchProvisionedProductsResponse


logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(message)s")
logger.setLevel(logging.INFO if os.getenv("logger_level") else logging.DEBUG)


class AWS:
    def __init__(self, aws_client_factory: IAWSClientFactory):
        self.aws_client_factory = aws_client_factory

    def _block_until_complete(
        self,
        task: Callable,
        args: list[Any],
        condition: Callable[..., bool],
        timeout: float = 5,
    ) -> None:

        response = task(*args)

        while condition(response):
            time.sleep(timeout)
            response = task(*args)
            logger.info(f"Request status: {response}")

    def __get_sc_products_for_account(self, account_id: str) -> list[str]:
        sc_product_ids = []
        sc_client = self.aws_client_factory.get_aws_client("servicecatalog")

        response = sc_client.search_provisioned_products(
            AccessLevelFilter={"Key": "Account", "Value": "self"},
            Filters={"SearchQuery": [account_id]},
        )

        try:
            sc_response = SearchProvisionedProductsResponse(**response)  # type: ignore[call-arg]
        except TypeError:
            return []
        
        for sc_provisioned_product in sc_response.ProvisionedProducts:
            if sc_provisioned_product.Status != "AVAILABLE":
                continue
            else:
                sc_product_ids.append(sc_provisioned_product.Id)
        
        return sc_product_ids

    def deregister_account(self, account_id: str) -> str:
        provisioned_products = []
        sc_client = self.aws_client_factory.get_aws_client("servicecatalog")
        provisioned_products = self.__get_sc_products_for_account(account_id)

        if provisioned_products is None:
            return f"No provisioned products found for {account_id}"
        
        for provisioned_product in provisioned_products:
            record_id_response = sc_client.terminate_provisioned_product(  # type: ignore[call-arg]
                ProvisionedProductId=provisioned_product, IgnoreErrors=True
            )

            record_id = record_id_response["RecordDetail"]["RecordId"]

            self._block_until_complete(
                task=lambda x: sc_client.describe_record(Id=record_id)[
                    "RecordDetail"
                ],
                args=[],
                condition=lambda x: x["Status"]
                in ["IN_PROGRESS", "IN_PROGRESS_IN_ERROR", "CREATED"],
            )

        return f"Succesfully terminated ControlTower account {account_id} from provisioned Service Catalog ID: {provisioned_products}"
