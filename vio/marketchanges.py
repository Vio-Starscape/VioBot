from enum import Enum

class MarketChangeType(Enum):
    NO_CHANGE = 0
    SOLD = 1
    COMPLETED = 2
    NEW = 3