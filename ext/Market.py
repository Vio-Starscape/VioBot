import discord
import logging
from discord import app_commands
from discord.ext import commands
from fuzzywuzzy import process
from main import Vio

logger = logging.getLogger(__name__)

class Market(commands.Cog, name="Market"):
    
    def __init__(self, bot: Vio):
        self.bot = bot

    @app_commands.command()
    async def item(self, interaction: discord.Interaction, item: str):
        """Get information about an item."""
        if item not in self.bot.items:
            await interaction.response.send_message("I haven't seen that item before! ;-;", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        logger.info(f"Getting information about item: {item} | By: {interaction.user}")
        items = await self.bot.db.get_item_history(item)
        latest_item = items[items.max_page]
        await interaction.followup.send(
            view=items.view,
            embed=latest_item.embed.set_image(url="attachment://graph.png"), 
            ephemeral=True,
            file=await items.graph_between_pages(items.min_page, items.max_page)
        )

    @item.autocomplete("item")
    async def item_autocomplete(self, ctx: commands.Context, item: str):
        logger.debug(f"Auto-completing item: {item}")
        if item != "":
            return [
                app_commands.Choice(name=item[0], value=item[0]) 
                for item in process.extractBests(item, self.bot.items, limit=25)
                ]
        return [
            app_commands.Choice(name=item, value=item) 
            for item in self.bot.items[:25]
            ]
    

async def setup(bot: Vio):
    await bot.add_cog(Market(bot))