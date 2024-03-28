import discord
import logging
import asyncio
from discord.ext import commands
from discord.ext import tasks
from vio import MarketChangeType, ListingChange, Listing, ListingType
from typing import List
from main import Vio

logger = logging.getLogger(__name__)

class Undercutter(commands.Cog):

    def __init__(self, bot: Vio):
        self.bot = bot
        self.__last_count_scanned: int = 0

        self.update.start()

    async def alert_user_about_undercut(self, user_id: int, item: str, undercutter: ListingChange, undercutted: Listing, all_listings: List[Listing]):
        user = self.bot.get_user(user_id)
        if not user:
            user = await self.bot.fetch_user(user_id)
        
        embed = discord.Embed(
            title=f"{'Undercut' if undercutted.type == ListingType.SELL else 'Overcut'} Alert!",
            description=f"**{undercutted.user.name}**'s **{'sell' if undercutted.type == ListingType.SELL else 'buy'}** "
            f"listing for **{item}** has been {'undercut' if undercutted.type == ListingType.SELL else 'overcut'} by **{undercutter.user.name}**"
        )

        listings_text = ""
        for listing in all_listings:
            if undercutter.original == listing:
                listings_text += f"-> **{listing.amount} @ {listing.price:,.2f} by {listing.user.name}**\n"
            elif undercutted == listing:
                listings_text += f"-> **{listing.amount} @ {listing.price:,.2f} by {listing.user.name}**\n"
            else:
                listings_text += f"{listing.amount} @ {listing.price:,.2f} by {listing.user.name}\n"
        embed.add_field(
            name="Listings",
            value=listings_text
        )

        await user.send(embed=embed)

    async def alert_user_about_completed(self, user_id: int, item: str, sale: ListingChange):
        user = self.bot.get_user(user_id)
        if not user:
            user = await self.bot.fetch_user(user_id)

        embed = discord.Embed(
            title=f"{sale.user.name}'s listing in {item} has disappeared!",
            description=f"{sale.user.name} has {'sold' if sale.previous.type == ListingType.SELL else 'bought'} **{sale.previous.amount:,} {item}**"
        )

        await user.send(embed=embed)


    @tasks.loop(minutes=5) # Run every 5 minutes
    async def update(self):
        """Update task

        Undercut checker.
        """
        logger.info("Checking for undercuts.")
        current_market = await self.bot.db.get_current_market()
        # Don't check if we've already scanned this market.
        if current_market.id == self.__last_count_scanned:
            logger.info("Already scanned this market.")
            return
        else:
            # Update the last scanned market count in db, to prevent rescanning.
            await self.bot.db.set_last_undercut_check(current_market.id)
            self.__last_count_scanned = current_market.id

        tracked_accounts = await self.bot.db.get_users_tracked_accounts()

        tasks = []

        for item in self.bot.items:
            item_instance = current_market[item]
            if not item_instance.valid:
                continue
            previous_instance = await self.bot.db.get_latest_valid_market_for_item_before(current_market.id, item)
            sell_changes, buy_changes = item_instance.process_changes(previous_instance) # Get the Changes
            for change in sell_changes:
                if change.type == MarketChangeType.NEW: #If the sell change is a New Listing
                    undercut_users: list[Listing] = []
                    for i in item_instance.sell: # Get all the users who were undercut
                        if i.price > change.original.price:
                            undercut_users.append(i)
                    seen = set()
                    unique = [x for x in undercut_users if x.user.id not in seen and not seen.add(x.user.id)] # Remove duplicates
                    for user in unique:
                        logger.debug(f"{user.user.name} got undercut by {change.original.user.name} in {item}!")
                        tracked = filter(lambda x: user.user.id in x["accounts"], tracked_accounts) # Get all the accounts that are tracking the user
                        for account in tracked: # Send the alert to all the accounts
                            tasks.append(self.alert_user_about_undercut(account['_id'], item, change, user, item_instance.sell))
                # elif change.type == MarketChangeType.COMPLETED: # if the sell change is a completed listing
                #     tracked = filter(lambda x: change.user.id in x["accounts"], tracked_accounts) # Get all the accounts that are tracking the user
                #     for account in tracked: # Send the alert to all the accounts
                #         tasks.append(self.alert_user_about_completed(account["_id"], item, change))

            for change in buy_changes: # Only difference is 'greater than' becomes 'less than'
                if change.type == MarketChangeType.NEW:
                    undercut_users: list[Listing] = []
                    for i in item_instance.buy:
                        if i.price < change.original.price:
                            undercut_users.append(i)
                    seen = set()
                    unique = [x for x in undercut_users if x.user.id not in seen and not seen.add(x.user.id)]
                    for user in unique:
                        logger.debug(f"{user.user.name} got undercut by {change.original.user.name} in {item}!")
                        tracked = filter(lambda x: user.user.id in x["accounts"], tracked_accounts)
                        for account in tracked:
                            tasks.append(self.alert_user_about_undercut(account['_id'], item, change, user, item_instance.buy))
                # elif change.type == MarketChangeType.COMPLETED:
                #     tracked = filter(lambda x: change.user.id in x["accounts"], tracked_accounts)
                #     for account in tracked:
                #         tasks.append(self.alert_user_about_completed(account["_id"], item, change))
        
        for task in tasks:
            await task
            await asyncio.sleep(1)
        logger.info(f"Undercut check complete. Messages sent: {len(tasks)}")
        

    @update.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()
        logger.info("Undercut checker ready.")
        self.__last_count_scanned = await self.bot.db.get_last_undercut_check()

async def setup(bot: Vio):
    await bot.add_cog(Undercutter(bot))