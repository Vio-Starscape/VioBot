from pydantic import BaseModel
from enum import Enum

from .robloxuser import RobloxUser

class MarketChangeType(Enum):
    NO_CHANGE = 0
    SOLD = 1
    COMPLETED = 2
    NEW = 3


class ListingChange(BaseModel):
    type: MarketChangeType
    price: float
    amount: int
    user: RobloxUser