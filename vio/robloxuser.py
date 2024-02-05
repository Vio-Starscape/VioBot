from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional

class RobloxUser(BaseModel):
    id: int = Field(alias="_id")
    name: str
    display_name: str = Field(alias="displayName")
    roblox_profile: Optional[str]
    roblox_tiny_profile: Optional[str]

    @root_validator(pre=True)
    def set_default_profiles(cls, values):
        id_ = values.get('_id')
        if id_ is not None:
            if values.get('roblox_profile') is None:
                values['roblox_profile'] = f"https://www.roblox.com/users/{id_}/profile"
            if values.get('roblox_tiny_profile') is None:
                values['roblox_tiny_profile'] = f"https://rblx.name/{id_}"
        return values