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
    undercut: bool = True
    overcut: bool = True
    completion: bool = False
    top: bool = False
    new: bool = False

    top_only: bool = False

    market: TrackedUserMarketSettings

class VioUser(BaseModel):
    discord_user: discord.User | discord.Member
    permissions: VioPermissions = VioPermissions()
    tracked_users: Dict[RobloxUser, TrackedUserSettings] = {}

    class Config:
        arbitrary_types_allowed = True

    def __hash__(self) -> int:
        return self.discord_user.id.__hash__()

    def mongo_dump(self):
        return {
            "_id": self.discord_user.id,
            "permissions": self.permissions.model_dump(),
            "tracked_users": {
                user.id: settings.model_dump() for user, settings in self.tracked_users.items()
            }
        }

    @property
    def embed(self):
        embed = discord.Embed(
            title=f"Settings for {self.discord_user.name}"
        )

        users = list(self.tracked_users.keys())

        chunked_users = [
            [f"{user.name}" for user in users[i:i + 10]]
            for i in range(0, len(users), 10)
        ]

        embed.add_field(
            name=f"Tracked Users ({len(self.tracked_users)})",
            value="\n".join(chunked_users[0]) if len(users) > 0 else "None"
        )

        for current_chunk in chunked_users[1:]:
            embed.add_field(
                name="‎",
                value="\n".join(current_chunk)
            )

        return embed
    
    def view(self, bot: "Vio"):
        if len(self.tracked_users) == 0:
            return None
        return UndercutSettingsView(self, bot)
    
class UserSelect(discord.ui.Select):

    def __init__(self, users: List[discord.SelectOption], callback, **kwargs):
        if callback is not None:
            self.the_callback = callback
        super().__init__(placeholder="Select a User", options=users, max_values=1, min_values=1, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        await self.the_callback(interaction, int(self.values[0]))
    
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

class UndercutSettingsButton(discord.ui.Button):
        def __init__(self, callback, **kwargs):
            super().__init__(**kwargs)
            self.callback = callback
    
        async def callback(self, interaction: discord.Interaction):
            await self.callback(interaction)

class UndercutSettingsView(discord.ui.View):

    def __init__(self, settings: VioUser, bot: "Vio"):
        super().__init__(timeout=300)
        self.settings = settings
        self.bot = bot

        self.users = list(self.settings.tracked_users.keys())
        self.page = 0
        self.chunks = [
            [
                discord.SelectOption(
                    label=user.name,
                    value=str(user.id)
                ) for user in self.users[i:i + 25]
            ] for i in range(0, len(self.users), 25)]
        
        self.selected_user = None
        self.__build_view()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.settings.discord_user.id

    def __build_view(self):
        self.clear_items()
        if len(self.chunks) > 1:
            self.add_item(
                UndercutSettingsButton(
                    self.__decrement_page,
                    label="Previous",
                    row=1,
                    style=discord.ButtonStyle.primary,
                    disabled=(self.page == 0)
                )   
            )
            self.add_item(
                UndercutSettingsButton(
                    lambda x: None,
                    label=f"{self.page+1}/{len(self.chunks)}",
                    row=1,
                    disabled=True,
                    style=discord.ButtonStyle.secondary
                )
            )
            self.add_item(
                UndercutSettingsButton(
                    self.__increment_page,
                    label="Next",
                    row=1,
                    style=discord.ButtonStyle.primary,
                    disabled=(self.page == len(self.chunks) - 1)
                )
            )
        self.select_option = UserSelect(self.chunks[self.page], self.on_user_select, row=2)
        self.add_item(self.select_option)

        if self.selected_user:
            user_settings = self.settings.tracked_users[self.selected_user]
            self.add_item(
                UndercutSettingsButton(
                    self.toggle_undercut,
                    label=f"{'Activate' if not user_settings.undercut else 'Disable'} Undercut",
                    row=3,
                    style=discord.ButtonStyle.success if not user_settings.undercut else discord.ButtonStyle.danger,
                    disabled=False
                )
            )
            self.add_item(
                UndercutSettingsButton(
                    self.toggle_overcut,
                    label=f"{'Activate' if not user_settings.overcut else 'Disable'} Overcut",
                    row=3,
                    style=discord.ButtonStyle.success if not user_settings.overcut else discord.ButtonStyle.danger,
                    disabled=False
                )
            )
            self.add_item(
                UndercutSettingsButton(
                    self.toggle_completion,
                    label=f"{'Activate' if not user_settings.completion else 'Disable'} Completion",
                    row=3,
                    style=discord.ButtonStyle.success if not user_settings.completion else discord.ButtonStyle.danger,
                    disabled=False
                )
            )
            self.add_item(
                UndercutSettingsButton(
                    self.toggle_new,
                    label=f"{'Activate' if not user_settings.new else 'Disable'} New",
                    row=3,
                    style=discord.ButtonStyle.success if not user_settings.new else discord.ButtonStyle.danger,
                    disabled=False
                )
            )
            self.add_item(
                UndercutSettingsButton(
                    self.toggle_took_top,
                    label=f"{'Activate' if not user_settings.top else 'Disable'} Took Top",
                    row=4,
                    style=discord.ButtonStyle.success if not user_settings.top else discord.ButtonStyle.danger,
                    disabled=False
                )
            )
            self.add_item(
                UndercutSettingsButton(
                    self.toggle_top_only,
                    label=f"{'Activate' if not user_settings.top_only else 'Disable'} Top Only",
                    row=4,
                    style=discord.ButtonStyle.success if not user_settings.top_only else discord.ButtonStyle.danger,
                    disabled=False
                )
            )
            self.add_item(
                UndercutSettingsButton(
                    self.toggle_market_active,
                    label=f"{'Activate' if not user_settings.market.active else 'Disable'} Market Whitelist",
                    row=4,
                    style=discord.ButtonStyle.success if not user_settings.market.active else discord.ButtonStyle.danger,
                    disabled=False
                )
            )

    async def __increment_page(self, interaction: discord.Interaction):
        self.page += 1
        self.__build_view()
        await interaction.response.edit_message(view=self)
    
    async def __decrement_page(self, interaction: discord.Interaction):
        self.page -= 1
        self.__build_view()
        await interaction.response.edit_message(view=self)

    def __embed_from_selected_user(self):
        user = self.selected_user
        embed = discord.Embed(
            title=f"Settings for {user.name}",
            description=f"ID: {user.id}"
        )

        settings = self.settings.tracked_users[user]
        embed.add_field(
            name="Settings",
            value=f"Undercut: {settings.undercut}\n"
            f"Overcut: {settings.overcut}\n"
            f"Completion: {settings.completion}\n"
            f"New: {settings.new}\n"
            f"Top Only: {settings.top_only}"
        )

        embed.add_field(
            name="Market Whitelist Settings",
            value=f"Active: {settings.market.active}\n"
            f"Markets: {', '.join(settings.market.markets) if len(settings.market.markets) > 0 else 'None'}"
        )

        return embed
    
    async def __update_user_settings(self, interaction: discord.Interaction):
        await self.bot.db.update_user_settings(
            user_id=self.settings.discord_user.id,
            tracked_id=self.selected_user.id,
            settings=self.settings.tracked_users[self.selected_user]
        )
        self.__build_view()
        await interaction.response.edit_message(embed=self.__embed_from_selected_user(), view=self)
    
    async def toggle_undercut(self, interaction: discord.Interaction):
        self.settings.tracked_users[self.selected_user].undercut = not self.settings.tracked_users[self.selected_user].undercut
        await self.__update_user_settings(interaction)

    async def toggle_overcut(self, interaction: discord.Interaction):
        self.settings.tracked_users[self.selected_user].overcut = not self.settings.tracked_users[self.selected_user].overcut
        await self.__update_user_settings(interaction)

    async def toggle_completion(self, interaction: discord.Interaction):
        self.settings.tracked_users[self.selected_user].completion = not self.settings.tracked_users[self.selected_user].completion
        await self.__update_user_settings(interaction)

    async def toggle_new(self, interaction: discord.Interaction):
        self.settings.tracked_users[self.selected_user].new = not self.settings.tracked_users[self.selected_user].new
        await self.__update_user_settings(interaction)

    async def toggle_market_active(self, interaction: discord.Interaction):
        self.settings.tracked_users[self.selected_user].market.active = not self.settings.tracked_users[self.selected_user].market.active
        await self.__update_user_settings(interaction)

    async def toggle_top_only(self, interaction: discord.Interaction):
        self.settings.tracked_users[self.selected_user].top_only = not self.settings.tracked_users[self.selected_user].top_only
        await self.__update_user_settings(interaction)

    async def toggle_took_top(self, interaction: discord.Interaction):
        self.settings.tracked_users[self.selected_user].top = not self.settings.tracked_users[self.selected_user].top
        await self.__update_user_settings(interaction)

    async def on_user_select(self, interaction: discord.Interaction, user_id: int):
        # self.add_item(discord.ui.Button(style=discord.ButtonStyle.danger, label="Remove User", custom_id=f"remove_user_{user.id}"))
        self.selected_user = next(user for user in self.users if user.id == user_id)
        self.__build_view()
        await interaction.response.edit_message(embed=self.__embed_from_selected_user(), view=self)

    async def on_market_click(self, interaction: discord.Interaction):
        pass

    async def on_market_select(self, interaction: discord.Interaction, name: str):
        if name not in self.bot.items:
            await interaction.response.send_message("Market not found!", ephemeral=True)
            return
        # if name in self.settings.tracked_users[self.selected_user].market.markets:
