import discord

from pydantic import BaseModel, Field, root_validator
from typing import List, Awaitable

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
                value="\n".join([f"**{listing.item}** - {listing.amount} @ {listing.price:,.2f}" for listing in self.buy])
            )
        else:
            user_embed.add_field(
                name="Buy",
                value="No buy listings."
            )

        if len(self.sell) > 0:
            user_embed.add_field(
                name="Sell",
                value="\n".join([f"**{listing.item}** - {listing.amount} @ {listing.price:,.2f}" for listing in self.sell])
            )
        else:
            user_embed.add_field(
                name="Sell",
                value="No sell listings."
            )

        return user_embed

    def view(self, bot: "Vio", *, is_tracking: bool = False) -> "UserInstanceView":
        return UserInstanceView(self, bot=bot, is_tracking=is_tracking)
    
class TrackingButtonBase(discord.ui.Button):
    def __init__(self, label, style, callback):
        super().__init__(style=style, label=label)
        self.the_callback = callback

    async def callback(self, interaction: discord.Interaction):
        await self.the_callback(interaction, self)

class UserInstanceView(discord.ui.View):

    def __init__(self, user_instance: UserInstance, bot: "Vio", *, is_tracking: bool = False):
        super().__init__()
        self.bot = bot
        self.user_instance = user_instance
        self.is_tracking = is_tracking
        self.__update()

        self.message = None

    def __update(self):
        self.clear_items()
        if self.is_tracking:
            self.add_item(
                TrackingButtonBase(
                    label="Stop Tracking",
                    style=discord.ButtonStyle.danger,
                    callback=self.on_stop_tracking
                )
            )
        else:
            self.add_item(TrackingButtonBase(
                label="Track",
                style=discord.ButtonStyle.primary,
                callback=self.on_track))
            

    async def on_timeout(self) -> None:
        if self.message is not None:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)
        await super().on_timeout()

    async def on_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != interaction.message.interaction_metadata.user.id:
            await interaction.response.send_message("Run the command yourself to track this user.", ephemeral=True)
            return
        await self.bot.db.add_tracked_account(interaction.user.id, self.user_instance.user.id)
        self.is_tracking = True
        self.__update()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"Started tracking {self.user_instance.user.name}.", ephemeral=True)

    async def on_stop_tracking(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != interaction.message.interaction_metadata.user.id:
            await interaction.response.send_message("Run the command yourself to strop tracking this user.", ephemeral=True)
            return
        await self.bot.db.remove_tracked_account(interaction.user.id, self.user_instance.user.id)
        self.is_tracking = False
        self.__update()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"Stopped tracking {self.user_instance.user.name}.", ephemeral=True)
