import discord
from datetime import datetime
from pydantic import BaseModel, Field, root_validator
from typing import Dict

from .iteminstance import ItemInstance

class MarketInstance(BaseModel):
    id: int = Field(alias="_id")
    time_scanned: datetime
    items: Dict[str, ItemInstance]

    @root_validator(pre=True)
    def assign_ids(cls, values):
        id_ = values.get("_id")
        time_scan = values.get("time_scanned")
        items = values.get("items", {})
        for item in items.values():
            item["_id"] = id_
            item["time_scanned"] = time_scan
        return values

    def __getitem__(self, key: str) -> ItemInstance:
        try:
            return self.items[key]
        except KeyError:
            return ItemInstance(_id=self.id, time_scanned=self.time_scanned, name=key, buy=[], sell=[])