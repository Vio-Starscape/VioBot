from pydantic import BaseModel, Field, root_validator
from typing import List

from .listing import Listing

class UserInstance(BaseModel):
    user: int = Field(alias="_id")
    buy: List[Listing]
    sell: List[Listing]