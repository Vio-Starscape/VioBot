import discord
import logging
import asyncio
import time
from discord import app_commands
from discord.ext import commands
from fuzzywuzzy import process
from discord.ext import tasks
from vio import MarketChangeType, ListingChange, Listing, ListingType, VioUser, ItemInstance
from typing import List
from main import Vio

logger = logging.getLogger(__name__)

@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class Undercutter(commands.GroupCog, name="undercut"):

    def __init__(self, bot: Vio):
        self.bot = bot
        self.__last_count_scanned: int = 0
        self.__false_counter: int = 0

        if not self.bot.TESTING: # Do not want to start pinging people if I am just testing with Prod DB (Testing DB does not have up to date stats)
            self.update.start()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        logger.debug(f"Checking if {interaction.user} is allowed to use the undercut.")
        if await self.bot.db.is_user_allowed_undercut(interaction.user.id):
            return True
        await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        return False

    @app_commands.command(description="Settings for the Undercut pinger.")
    async def settings(self, interaction: discord.Interaction):
        """Settings for the Undercut Checker."""
        user = await self.bot.db.get_users_settings(interaction.user, self.bot)
        await interaction.response.send_message(
            embed=user.embed,
            view=user.view(self.bot),
            ephemeral=True
        )

    @app_commands.command(description="Whitelist a market for a certain user.")
    async def whitelist(self, interaction: discord.Interaction, user: int, market: str):
        tracked_accounts = await self.bot.db.get_users_settings(interaction.user, self.bot, roblox_list=self.bot.roblox_users)
        if user not in (roblox_user.id for roblox_user in tracked_accounts.tracked_users.keys()):
            await interaction.response.send_message("I haven't seen that user before! ;-;", ephemeral=True)
            return
        user, settings = next(filter(lambda x: x[0].id == user, tracked_accounts.tracked_users.items()))
        if market not in self.bot.items:
            await interaction.response.send_message("I haven't seen that item before! ;-;", ephemeral=True)
            return
        if market in tracked_accounts.tracked_users[user].market.markets:
            await interaction.response.send_message(f"{market} is already whitelisted for {user.name}.", ephemeral=True)
            return
        try:
            settings.market.markets.append(market)
            await self.bot.db.update_user_settings(interaction.user.id, user.id, settings)
            await interaction.response.send_message(f"Whitelisted {market} for {user.name}.", ephemeral=True)
        except KeyError:
            await interaction.response.send_message(f"Failed to whitelist {market} for {user.name}.", ephemeral=True)

    @app_commands.command(description="Delist a market for a certain user.")
    async def delist(self, interaction: discord.Interaction, user: int, market: str):
        tracked_accounts = await self.bot.db.get_users_settings(interaction.user, self.bot, roblox_list=self.bot.roblox_users)
        if user not in (roblox_user.id for roblox_user in tracked_accounts.tracked_users.keys()):
            await interaction.response.send_message("I haven't seen that user before! ;-;", ephemeral=True)
            return
        user, settings = next(filter(lambda x: x[0].id == user, tracked_accounts.tracked_users.items()))
        if market not in self.bot.items:
            await interaction.response.send_message("I haven't seen that item before! ;-;", ephemeral=True)
            return
        if market not in settings.market.markets:
            await interaction.response.send_message(f"{market} is not whitelisted for {user.name}.", ephemeral=True)
            return
        try:
            settings.market.markets.remove(market)
            await self.bot.db.update_user_settings(interaction.user.id, user.id, settings)
            await interaction.response.send_message(f"Delisted {market} for {user.name}.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(f"Failed to delist {market} for {user.name}.", ephemeral=True)


    @whitelist.autocomplete("user")
    async def user_autocomplete(self, interaction: discord.Interaction, option: str):
        if await self.bot.db.is_user_allowed_undercut(interaction.user.id):
            tracked_accounts = await self.bot.db.get_users_settings(interaction.user, self.bot, roblox_list=self.bot.roblox_users)
            choices = [
                app_commands.Choice(name=user.name, value=user.id) 
                for user in tracked_accounts.tracked_users.keys()
                if option.lower() in user.name.lower()
            ]
            return choices[:25]
        return [app_commands.Choice(name="You do not have permission.", value="no-permission")]
    
    @delist.autocomplete("user")
    async def delist_user_autocomplete(self, interaction: discord.Interaction, option: str):
        if await self.bot.db.is_user_allowed_undercut(interaction.user.id):
            tracked_accounts = await self.bot.db.get_users_settings(interaction.user, self.bot, roblox_list=self.bot.roblox_users)
            choices = [
                app_commands.Choice(name=user.name, value=user.id) 
                for user in tracked_accounts.tracked_users.keys()
                if option.lower() in user.name.lower()
            ]
            return choices[:25]
        return [app_commands.Choice(name="You do not have permission.", value="no-permission")]
    
    @delist.autocomplete("market")
    async def delist_market_autocomplete(self, interaction: discord.Interaction, option: str):
        if await self.bot.db.is_user_allowed_undercut(interaction.user.id):
            try:
                tracked_accounts = await self.bot.db.get_users_settings(interaction.user, self.bot, roblox_list=self.bot.roblox_users)
                user, settings = next(filter(lambda x: x[0].id == int(interaction.namespace["user"]), tracked_accounts.tracked_users.items()))
                choices = [
                    app_commands.Choice(name=i, value=i) 
                    for i in settings.market.markets
                    if option.lower() in i.lower()
                    ]
                return choices[:25]
            except KeyError:
                return []
        return [app_commands.Choice(name="You do not have permission.", value=10)]

    @whitelist.autocomplete("market")
    async def whitelist_market_autocomplete(self, interaction: discord.Interaction, option: str):
        if await self.bot.db.is_user_allowed_undercut(interaction.user.id):
            try:
                tracked_accounts = await self.bot.db.get_users_settings(interaction.user, self.bot, roblox_list=self.bot.roblox_users)
                user, settings = next(filter(lambda x: x[0].id == int(interaction.namespace["user"]), tracked_accounts.tracked_users.items()))
                choices = [
                    app_commands.Choice(name=i, value=i) 
                    for i in self.bot.items
                    if option.lower() in i.lower() and i.lower() not in [j.lower() for j in settings.market.markets]
                    ]
                return choices[:25]
            except KeyError:
                return []
        return [app_commands.Choice(name="You do not have permission.", value=10)]

    def __new_listing(self, item: str, listing: Listing, all_listings: List[Listing]):
        
        embed = discord.Embed(
            title=f"New {'Buy' if listing.type == ListingType.BUY else 'Sell'} Listing Alert!",
            description=f"**{listing.user.name}** has listed **{listing.amount:,} {item}** for **{listing.price:,.2f}**"
        )

        listings_text = ""
        for i in all_listings:
            if i == listing:
                listings_text += f"-> **{i.amount} @ {i.price:,.2f} by {i.user.name}**\n"
            else:
                listings_text += f"{i.amount} @ {i.price:,.2f} by {i.user.name}\n"

        embed.add_field(
            name="Listings",
            value=listings_text
        )

        return embed

    def __undercut(self, item: str, undercutter: ListingChange, undercutted: Listing, all_listings: List[Listing]):
        
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

        return embed

    def __completed(self, item: str, sale: ListingChange):

        embed = discord.Embed(
            title=f"{sale.user.name}'s {'buy' if sale.previous.type == ListingType.BUY else 'sell'} listing in {item} has disappeared!",
            description=f"{sale.user.name} has {'sold' if sale.previous.type == ListingType.SELL else 'bought'} **{sale.previous.amount:,} {item}**"
        )

        return embed
    
    def __changed(self, item: str, change: ListingChange):
        embed = discord.Embed(
            title=f"{change.user.name} Update!",
            description=f"**{change.user.name}** has {'sold' if change.previous.type == ListingType.SELL else 'bought'} "
                        f"**{change.previous.amount - change.original.amount:,} {item}** for **{change.previous.price:,.2f}** for a total of **{change.previous.price * (change.previous.amount - change.original.amount):,.2f}**"
        )
        
        embed.add_field(
            name="Previous",
            value=f"**{change.previous.amount} @ {change.previous.price:,.2f}**"
        )
        
        embed.add_field(
            name="Current",
            value=f"**{change.original.amount} @ {change.original.price:,.2f}**"
        )

        return embed
    
    def __took_top_spot(self, item: str, listing: ListingChange, all_listings: List[Listing]):
        embed = discord.Embed(
            title=f"Top Listing Alert!",
            description=f"**{listing.user.name}** has taken the top spot for **{item}** with **{listing.amount:,} {item}** for **{listing.price:,.2f}**"
        )

        listings_text = ""
        for i in all_listings:
            if i == listing:
                listings_text += f"-> **{i.amount} @ {i.price:,.2f} by {i.user.name}**\n"
            else:
                listings_text += f"{i.amount} @ {i.price:,.2f} by {i.user.name}\n"

        embed.add_field(
            name="Listings",
            value=listings_text
        )

        return embed


    @tasks.loop(seconds=30, reconnect=True) # Run every 10 seconds
    async def update(self):
        """Update task

        Undercut checker.
        """
        current_market = await self.bot.db.get_current_market()

        # Don't check if we've already scanned this market.
        if current_market.id == self.__last_count_scanned:
            logger.debug("Already scanned this market.")
            if self.__false_counter > 60: # Ping Meaning when shit be broken
                self.__false_counter = 0
                owner = await self.bot.fetch_user(self.bot.owner_id or 160506586408812545)
                await owner.send("Undercut checker is stuck in a loop. Scraper might be broken.")
            self.__false_counter += 1
            return
        else:
            # Update the last scanned market count in db, to prevent rescanning.
            self.__false_counter = 0
            await self.bot.db.set_last_undercut_check(current_market.id)
            self.__last_count_scanned = current_market.id
        logger.debug("Checking for undercuts.")
        
        start = time.perf_counter()

        tracked_accounts = await self.bot.db.get_users_tracked_accounts(self.bot)

        tasks: dict[VioUser, List[discord.Embed]] = {}

        for item in self.bot.items:
            item_instance = current_market[item]
            if not item_instance.valid:
                continue
            previous_instance = await self.bot.db.get_latest_valid_market_for_item_before(current_market.id, item)
            if previous_instance is None:
                continue
            sell_changes, buy_changes = item_instance.process_changes(previous_instance) # Get the Changes

            # Get the previous top sell user
            previous_top_sell_user = previous_instance.sell[0].user if previous_instance.sell else None

            # Get the current top sell user
            current_top_sell_user = item_instance.sell[0].user if item_instance.sell else None

            # If the top sell user has changed
            if previous_top_sell_user and current_top_sell_user and previous_top_sell_user != current_top_sell_user:
                logger.debug(f"{current_top_sell_user.name} has taken the top spot in {item}!")
                tracked = filter(lambda x: current_top_sell_user in x.tracked_users.keys(), tracked_accounts)
                for account in tracked:
                    settings = account.tracked_users[current_top_sell_user]
                    if settings.top and ((settings.market.active and item in settings.market.markets) or not settings.market.active):
                        tasks.setdefault(account, []).append(self.__took_top_spot(item, item_instance.sell[0], item_instance.sell))

            for change in sell_changes:
                if change.type == MarketChangeType.NEW: #If the sell change is a New Listing
                    logger.debug(f"{change.original.user.name} listed {change.original.amount} {item} for {change.original.price:,.2f}!")

                    # Get users who are tracking the person who undercut
                    tracked = filter(lambda x: change.original.user in x.tracked_users.keys(), tracked_accounts)
                    for account in tracked:
                        settings = account.tracked_users[change.original.user]
                        if settings.new and ((settings.market.active and item in settings.market.markets) or not settings.market.active): # Add the embed to this account's tasks
                            tasks.setdefault(account, []).append(self.__new_liOvercutsting(item, change.original, item_instance.sell))
                    
                    # Get all the users who were undercut
                    undercut_users: list[Listing] = []
                    for i in item_instance.sell:
                        if i.price > change.original.price:
                            undercut_users.append(i)
                    seen = set()
                    unique = [x for x in undercut_users if x.user.id not in seen and not seen.add(x.user.id)] # Remove duplicates

                    for user in unique:
                        logger.debug(f"{user.user.name} got undercut by {change.original.user.name} in {item}!")
                        tracked = filter(lambda x: user.user in x.tracked_users.keys(), tracked_accounts) # Get all the accounts that are tracking the user
                        for account in tracked: # Send the alert to all the accounts
                            settings = account.tracked_users[user.user]
                            if settings.undercut and ((settings.top_only and user == item_instance.sell[1]) or not settings.top_only) and ((settings.market.active and item in settings.market.markets) or not settings.market.active):
                                tasks.setdefault(account, []).append(self.__undercut(item, change, user, item_instance.sell))

                elif change.type == MarketChangeType.COMPLETED: # if the sell change is a completed listing
                    tracked = filter(lambda x: change.previous.user in x.tracked_users.keys(), tracked_accounts) # Get all the accounts that are tracking the user
                    for account in tracked: # Send the alert to all the accounts
                        settings = account.tracked_users[change.previous.user]
                        if settings.completion and ((settings.market.active and item in settings.market.markets) or not settings.market.active):
                            tasks.setdefault(account, []).append(self.__completed(item, change))
                            
                elif change.type == MarketChangeType.SOLD:
                    logger.debug(f"{change.previous.user.name} sold {change.previous.amount - change.original.amount} {item} for {change.previous.price:,.2f}!")
                    tracked = filter(lambda x: change.previous.user in x.tracked_users.keys(), tracked_accounts)
                    for account in tracked:
                        settings = account.tracked_users[change.previous.user]
                        if settings.changes and ((settings.market.active and item in settings.market.markets) or not settings.market.active):
                            tasks.setdefault(account, []).append(self.__changed(item, change))


            # Get the previous top buy user
            previous_top_sell_user = previous_instance.buy[0].user if previous_instance.buy else None

            # Get the current top buy user
            current_top_sell_user = item_instance.buy[0].user if item_instance.buy else None

            # If the top buy user has changed
            if previous_top_sell_user and current_top_sell_user and previous_top_sell_user != current_top_sell_user:
                logger.debug(f"{current_top_sell_user.name} has taken the top spot in {item}!")
                tracked = filter(lambda x: current_top_sell_user in x.tracked_users.keys(), tracked_accounts)
                for account in tracked:
                    settings = account.tracked_users[current_top_sell_user]
                    if settings.top and ((settings.market.active and item in settings.market.markets) or not settings.market.active):
                        tasks.setdefault(account, []).append(self.__took_top_spot(item, item_instance.buy[0], item_instance.buy))

            for change in buy_changes: # Only difference is 'greater than' becomes 'less than'
                if change.type == MarketChangeType.NEW: #If the sell change is a New Listing
                    logger.debug(f"{change.original.user.name} listed {change.original.amount} {item} for {change.original.price:,.2f}!")

                    # Get users who are tracking the person who undercut
                    tracked = filter(lambda x: change.original.user in x.tracked_users.keys(), tracked_accounts)
                    for account in tracked:
                        settings = account.tracked_users[change.original.user]
                        if settings.new and ((settings.market.active and item in settings.market.markets) or not settings.market.active): # Add the embed to this account's tasks
                            tasks.setdefault(account, []).append(self.__new_listing(item, change.original, item_instance.buy))
                    
                    # Get all the users who were undercut
                    undercut_users: list[Listing] = []
                    for i in item_instance.sell:
                        if i.price < change.original.price:
                            undercut_users.append(i)
                    seen = set()
                    unique = [x for x in undercut_users if x.user.id not in seen and not seen.add(x.user.id)] # Remove duplicates

                    for user in unique:
                        logger.debug(f"{user.user.name} got undercut by {change.original.user.name} in {item}!")
                        tracked = filter(lambda x: user.user in x.tracked_users.keys(), tracked_accounts) # Get all the accounts that are tracking the user
                        for account in tracked: # Send the alert to all the accounts
                            settings = account.tracked_users[user.user]
                            if settings.overcut and ((settings.top_only and user == item_instance.buy[1]) or not settings.top_only) and ((settings.market.active and item in settings.market.markets) or not settings.market.active):
                                tasks.setdefault(account, []).append(self.__undercut(item, change, user, item_instance.buy))

                elif change.type == MarketChangeType.COMPLETED: # if the sell change is a completed listing
                    tracked = filter(lambda x: change.previous.user in x.tracked_users.keys(), tracked_accounts) # Get all the accounts that are tracking the user
                    for account in tracked: # Send the alert to all the accounts
                        settings = account.tracked_users[change.previous.user]
                        if settings.completion and ((settings.market.active and item in settings.market.markets) or not settings.market.active):
                            tasks.setdefault(account, []).append(self.__completed(item, change))
                            
                elif change.type == MarketChangeType.SOLD:
                    logger.debug(f"{change.previous.user.name} sold {change.previous.amount - change.original.amount} {item} for {change.previous.price:,.2f}!")
                    tracked = filter(lambda x: change.previous.user in x.tracked_users.keys(), tracked_accounts)
                    for account in tracked:
                        settings = account.tracked_users[change.previous.user]
                        if settings.changes and ((settings.market.active and item in settings.market.markets) or not settings.market.active):
                            tasks.setdefault(account, []).append(self.__changed(item, change))

        for account, embeds in tasks.items():
            chunks = [embeds[i:i+10] for i in range(0, len(embeds), 10)]
            for embed in chunks:
                try:    
                    await account.discord_user.send(embeds=embed)
                    await asyncio.sleep(0.1)
                except:
                    logger.error(f"Failed to send message to {account.discord_user}.")
                    break
                
        end = time.perf_counter()
        
        logger.debug(f"Undercut check complete. {sum([len(i) for i in tasks.values()])} messages sent to {len(tasks)} people. Took {end - start:.2f} seconds.")

    @update.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()
        logger.info("Undercut checker ready.")
        self.__last_count_scanned = await self.bot.db.get_last_undercut_check()

async def setup(bot: Vio):
    await bot.add_cog(Undercutter(bot))