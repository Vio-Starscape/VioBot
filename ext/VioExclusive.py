import discord
import logging
from discord import app_commands
from discord.ext import commands
from main import Vio

from vio import AffiliationModal

logger = logging.getLogger(__name__)

class VioGroup(commands.GroupCog, name="vio"):

    def __init__(self, bot: Vio):
        self.bot = bot
    
    @app_commands.command(description="(Owner Only) Pop up a modal for you to submit an affiliation.")
    async def affiliate(self, interaction: discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return
        """Get the affiliate link for Vio."""
        logger.info(f"Affiliation command called by {interaction.user.name} ({interaction.user.id})")
        await interaction.response.send_modal(AffiliationModal(self.bot))

    


async def setup(bot: Vio):
    await bot.add_cog(VioGroup(bot), guild=bot.main_guild)