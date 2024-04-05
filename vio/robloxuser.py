from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional

class RobloxUser(BaseModel):
    id: int = Field(alias="_id")
    name: str
    display_name: str = Field(alias="displayName")
    roblox_profile: str
    roblox_tiny_profile: str

    def __hash__(self) -> int:
        return self.id.__hash__()

    @root_validator(pre=True)
    def set_default_profiles(cls, values):
        id_ = values.get('_id')
        if id_ is not None:
            values['roblox_profile'] = f"https://www.roblox.com/users/{id_}/profile"
            values['roblox_tiny_profile'] = f"https://rblx.name/{id_}"
        return values