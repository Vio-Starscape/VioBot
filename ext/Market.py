import discord
import logging
from discord import app_commands
from discord.ext import commands
from fuzzywuzzy import process
from main import Vio

logger = logging.getLogger(__name__)

class Market(commands.GroupCog, name="market"):
    
    def __init__(self, bot: Vio):
        self.bot = bot

    @app_commands.command()
    async def item(self, interaction: discord.Interaction, item: str):
        """Get information about an item."""
        if item not in self.bot.items:
            await interaction.response.send_message("I haven't seen that item before! ;-;", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        logger.info(f"Getting information about item: {item} | By: {interaction.user} | In: {interaction.guild.name} (ID: {interaction.guild.id})")
        items = await self.bot.db.get_item_history(item)
        selected = items.latest_usable()
        await interaction.followup.send(
            # view=items.view,
            embed=selected.embed.set_image(url="attachment://graph.png"), 
            ephemeral=True,
            file=await items.graph_between_pages(items.max_page-2000, items.max_page)
        )

    @item.autocomplete("item")
    async def item_autocomplete(self, ctx: commands.Context, item: str):
        logger.debug(f"Auto-completing item: {item}")
        if item != "":
            return [
                app_commands.Choice(name=i[0], value=i[0]) 
                for i in process.extractBests(item, self.bot.items, limit=25)
                if item.lower() in i[0].lower()
                ]
        return [
            app_commands.Choice(name=item, value=item) 
            for item in self.bot.items[:25]
            ]
    
    @app_commands.command()
    async def user(self, interaction: discord.Interaction, vendor: str):
        """Get information about a user."""
        try:
            vendor = int(vendor)
            if vendor not in [roblox_user.id for roblox_user in self.bot.roblox_users]:
                await interaction.response.send_message("I haven't seen that user before! ;-;", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("I haven't seen that user before! ;-;", ephemeral=True)
            return
        
        await interaction.response.defer(thinking=True)

        selected_user = next(roblox_user for roblox_user in self.bot.roblox_users if roblox_user.id == vendor)

        logger.info(f"Getting information about user: {selected_user} | By: {interaction.user} | In: {interaction.guild.name} (ID: {interaction.guild.id})")
        user_instance = await self.bot.db.get_current_market_for_user(selected_user)
        await interaction.followup.send(embed=user_instance.embed, ephemeral=True)

    @user.autocomplete("vendor")
    async def user_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        logger.debug(f"Auto-completing user: {current}")
        response_list = []
        try:
            user_id = int(current)
            response_list = [
                app_commands.Choice(name=user.name, value=str(user.id))
                for user in self.bot.roblox_users if user.name.lower().startswith(current.lower())
                ] + [
                app_commands.Choice(name=user.name, value=str(user.id))
                for user in self.bot.roblox_users if str(user.id).startswith(str(user_id))
                ]
        except ValueError:
            response_list = [
                app_commands.Choice(name=user.name, value=str(user.id)) 
                for user in self.bot.roblox_users if user.name.lower().startswith(current.lower())
                ]
        return response_list[:25]

async def setup(bot: Vio):
    await bot.add_cog(Market(bot))