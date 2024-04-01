import discord
import asyncio
import logging
import random
from discord import app_commands
from discord.ext import commands
from fuzzywuzzy import process
from main import Vio

logger = logging.getLogger(__name__)

class Market(commands.GroupCog, name="market"):
    
    def __init__(self, bot: Vio):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction):
        if random.randint(0, 1) != 1:
            logger.warning(f"Command failed cause of April Fools.")
            responses = [
                "WHERE AM I, WHO ARE YOU?!",
                "WHAT DO YOU WANT FROM ME?!",
                "I DON'T KNOW YOU!",
                "I'M NOT TALKING TO YOU!",
                "WHIPPER SNAPPER!, GET OFF MY LAWN!",
                "I'M TOO OLD FOR THIS!",
                "I'M NOT IN THE MOOD!",
            ]
            await interaction.response.send_message(random.choice(responses), ephemeral=True)
            return False
        else:
            return True

    @app_commands.command()
    async def item(self, interaction: discord.Interaction, item: str):
        """Get information about an item."""
        if item not in self.bot.items:
            await interaction.response.send_message("I haven't seen that item before! ;-;", ephemeral=True)
            return
        # await interaction.response.defer(thinking=True)
        await interaction.response.send_message("Alrighty gimmie a minute to find where I put that information!")
        delay = random.randint(1, 300)
        logger.info(f"Getting information about item: {item} | By: {interaction.user} | "
                    f"In: {interaction.guild.name if interaction.guild else interaction.channel.recipient.name}"
                    f" (ID: {interaction.guild.id if interaction.guild else interaction.channel.id}) | Delay: {delay} seconds")
        await asyncio.sleep(delay)
        items = await self.bot.db.get_item_history(item, depth=2010)
        selected = items.latest_usable()
        await interaction.followup.send(
            # view=items.view,
            embed=selected.embed.set_image(url="attachment://graph.png"), 
            ephemeral=True,
            file=await items.graph()
        )
    
    @item.error
    async def item_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            logger.warning(f"Command failed cause of April Fools.")

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
            if vendor not in (roblox_user.id for roblox_user in self.bot.roblox_users):
                await interaction.response.send_message("I haven't seen that user before! ;-;", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("I haven't seen that user before! ;-;", ephemeral=True)
            return
        
        await interaction.response.send_message("Alrighty gimmie a minute to find where I put that information!")
        delay = random.randint(1, 300)
        selected_user = next(roblox_user for roblox_user in self.bot.roblox_users if roblox_user.id == vendor)
        logger.info(f"Getting information about user: {selected_user.name} | By: {interaction.user} | "
                    f"In: {interaction.guild.name if interaction.guild else interaction.channel.recipient.name}"
                    f" (ID: {interaction.guild.id if interaction.guild else interaction.channel.id}) | Delay: {delay} seconds")
        await asyncio.sleep(delay)

        user_instance = await self.bot.db.get_current_market_for_user(selected_user)

        if await self.bot.db.does_user_have_undercut_permission(interaction.user.id):
            tracking = await self.bot.db.is_user_tracking_account(interaction.user.id, selected_user.id)

            await interaction.followup.send(
                embed=user_instance.embed,
                view=user_instance.view(self.bot, is_tracking=tracking),
                # ephemeral=True
            )
        else:
            await interaction.followup.send(
                embed=user_instance.embed,
                # ephemeral=True
            )

    @user.error
    async def user_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, commands.CheckFailure):
            logger.warning(f"Command failed cause of April Fools.")

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