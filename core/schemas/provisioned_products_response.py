from dataclasses import dataclass
from typing import Literal


@dataclass
class ProvisionedProduct:
    Id: str
    Status: Literal["AVAILABLE", "UNDER_CHANGE", "TAINTED", "ERROR", "PLAN_IN_PROGRESS"]


@dataclass()
class SearchProvisionedProductsResponse:
    ProvisionedProducts: list[ProvisionedProduct]
