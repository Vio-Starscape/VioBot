import discord
from .robloxuser import RobloxUser
from pydantic import BaseModel
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from main import Vio

class VioPermissions(BaseModel):
    evaluation: bool = False
    undercut: bool = False

class TrackedUserMarketSettings(BaseModel):
    active: bool = False
    markets: List[str]

class TrackedUserSettings(BaseModel):
    undercut: bool
    overcut: bool
    completion: bool

    market: TrackedUserMarketSettings

class VioUser(BaseModel):
    discord_user: discord.User
    permissions: VioPermissions = VioPermissions()
    tracked_users: Dict[RobloxUser, TrackedUserSettings] = {}

    class Config:
        arbitrary_types_allowed = True

    @property
    def embed(self):
        embed = discord.Embed(
            title=f"Settings for {self.discord_user.name}"
        )

        embed.add_field(
            name="Tracked Users",
            value="\n".join([f"{user.name}" for user, settings in self.tracked_users.items()])
        )

        return embed
    
    def view(self, bot: "Vio"):
        return UndercutSettingsView(self, bot)
    
class UserSelect(discord.ui.Select):

    def __init__(self, users: List[RobloxUser], callback=None):
        self.users = users
        options = [
            discord.SelectOption(
                label=user.name,
                value=str(user.id)
            )
            for user in users
        ]
        if callback is not None:
            self.the_callback = callback
        super().__init__(placeholder="Select a User", options=options, max_values=1, min_values=1)

    async def callback(self, interaction: discord.Interaction):
        user = next((user for user in self.users if user.id == int(self.values[0])), None)
        await self.the_callback(interaction, user)
    

class UndercutSettingsModal(discord.ui.Modal):
    name = discord.ui.TextInput(
        label="Market Name",
        placeholder="Korrelite"
    )

    def __init__(self, callback):
        super().__init__(timeout=None, title="Undercut Settings")
        self.callback = callback

    async def on_select(self, interaction: discord.Interaction):
        await self.callback(interaction)

class UndercutSettingsView(discord.ui.View):

    def __init__(self, settings: VioUser, bot: "Vio"):
        super().__init__()
        self.settings = settings
        self.bot = bot
        self.add_item(UserSelect([user for user in self.settings.tracked_users.keys()], self.on_user_select))

    async def __clear_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                self.remove_item(item)

    def __embed_from_selected_user(self, user: RobloxUser):
        embed = discord.Embed(
            title=f"Settings for {user.name}",
            description="Settings for the Tracked User."
        )

        settings = self.settings.tracked_users[user]
        embed.add_field(
            name="Settings",
            value=f"Undercut: {settings.undercut}\n"
            f"Overcut: {settings.overcut}\n"
            f"Completion: {settings.completion}"
        )

        embed.add_field(
            name="Market Settings",
            value=f"Active: {settings.market.active}\n"
            f"Markets: {', '.join(settings.market.markets) if len(settings.market.markets) > 0 else 'None'}"
        )

        return embed



    async def on_user_select(self, interaction: discord.Interaction, user: RobloxUser):
        # self.add_item(discord.ui.Button(style=discord.ButtonStyle.danger, label="Remove User", custom_id=f"remove_user_{user.id}"))
        self.selected_user = user
        await interaction.response.edit_message(embed=self.__embed_from_selected_user(user), view=self)

    async def on_market_click(self, interaction: discord.Interaction):
        pass

    async def on_market_select(self, interaction: discord.Interaction, name: str):
        if name not in self.bot.items:
            await interaction.response.send_message("Market not found!", ephemeral=True)
            return
        # if name in self.settings.tracked_users[self.selected_user].market.markets:
