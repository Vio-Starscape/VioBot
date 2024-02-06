import discord

from pydantic import BaseModel, Field, root_validator
from typing import List

from .listing import Listing
from .robloxuser import RobloxUser

class UserInstance(BaseModel):
    user: RobloxUser
    buy: List[Listing]
    sell: List[Listing]


    @property
    def embed(self):
        user_embed = discord.Embed(
            title=f"{self.user.name}'s Listings",
            description=f"**ID:** {self.user.id}",
            color=0x2F3136
        )

        if len(self.buy) > 0:
            user_embed.add_field(
                name="Buy",
                value="\n".join([f"**{listing.item}** - {listing.amount} @ {listing.price}" for listing in self.buy])
            )
        else:
            user_embed.add_field(
                name="Buy",
                value="No buy listings."
            )

        if len(self.sell) > 0:
            user_embed.add_field(
                name="Sell",
                value="\n".join([f"**{listing.item}** - {listing.amount} @ {listing.price}" for listing in self.sell])
            )
        else:
            user_embed.add_field(
                name="Sell",
                value="No sell listings."
            )

        user_embed.timestamp = discord.utils.utcnow()

        return user_embed