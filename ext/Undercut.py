import discord
import logging
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
from fuzzywuzzy import process
from vio import MarketChangeType
from main import Vio

logger = logging.getLogger(__name__)

class Undercutter(commands.Cog):

    def __init__(self, bot: Vio):
        self.bot = bot

        self.__last_count_scanned: int = 0

    

    @tasks.loop(minutes=5) # Run every 10 minutes
    async def update(self):
        """Update task

        Undercut checker.
        """
        logger.info("Checking for undercuts.")
        current_market = await self.bot.db.get_current_market()
        # Don't check if we've already scanned this market.
        if current_market.id == self.__last_count_scanned:
            return
    
        self.__last_count_scanned = current_market.id

        for item in self.bot.items:
            item_instance = current_market[item]
            if not item_instance.valid:
                continue
            previous_instance = self.bot.db.get_latest_valid_market_for_item_before(current_market.id, item)
            sell_changes, buy_changes = item_instance.process_changes(previous_instance)
            for change in sell_changes:
                if change.type == MarketChangeType.NEW:
            for listing in item_instance.sell:
                for user in self.bot.roblox_users:
                    user_instance = current_market[user.id]
                    for user_listing in user_instance.buy:
                        if listing.item == user_listing.item and listing.price < user_listing.price:
                            logger.info(f"Undercut found! {user.name} is selling {listing.item} @ {listing.price} but {item.name} is buying @ {user_listing.price}")
            for listing in item_instance.buy:
                for user in self.bot.roblox_users:
                    user_instance = current_market[user.id]
                    for user_listing in user_instance.sell:
                        if listing.item == user_listing.item and listing.price > user_listing.price:
                            logger.info(f"Undercut found! {user.name} is buying {listing.item} @ {listing.price} but {item.name} is selling @ {user_listing.price}")



async def setup(bot: Vio):
    await bot.add_cog(Undercutter(bot))