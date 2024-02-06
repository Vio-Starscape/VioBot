from pydantic import BaseModel, root_validator
from enum import Enum

from .robloxuser import RobloxUser

class ListingType(Enum):
    BUY = 1
    SELL = 2

class Listing(BaseModel):
    item: str
    price: float
    amount: int
    user: RobloxUser
    type: ListingType

    @root_validator(pre=True)
    def convert_list_to_dict(cls, values) -> dict:
        if isinstance(values, list):
            return {
                'price': values[0],
                'amount': values[1],
                'user': values[2],
                'type': values[3],
                'item': values[4]
            }
        return values
