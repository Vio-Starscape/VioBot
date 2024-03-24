import discord

from pydantic import BaseModel, Field, root_validator
from typing import List

from .listing import Listing
from .robloxuser import RobloxUser

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Vio

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

    def view(self, bot: Vio) -> "UserInstanceView":
        return UserInstanceView(self, bot=bot)
    
class UserInstanceView(discord.ui.View):

    def __init__(self, user_instance: UserInstance, bot: Vio):
        super().__init__()
        self.bot = bot
        self.user_instance = user_instance

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        self.stop()

    @discord.ui.button(label="This is me!", style=discord.ButtonStyle.primary)
    async def is_me(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Yes, it's you!", ephemeral=True)

    @discord.ui.button(label="Track Changes", style=discord.ButtonStyle.secondary)
    async def track(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Tracking this user...", ephemeral=True)
