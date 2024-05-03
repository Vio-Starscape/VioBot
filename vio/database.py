import asyncio
import discord
import logging
from datetime import timezone
from typing import Optional, TYPE_CHECKING
from motor.motor_asyncio import AsyncIOMotorClient

from .marketinstance import MarketInstance
from .iteminstance import ItemInstance
from .historyinstance import MarketHistoryInstance
from .robloxuser import RobloxUser
from .userinstance import UserInstance
from .clientsettings import VioUser, TrackedUserMarketSettings

from PIL import Image
from io import BytesIO

if TYPE_CHECKING:
    from main import Vio

logger = logging.getLogger(__name__)

class VioDB:

    def __init__(self, uri: str, database: str = "Vio"):
        self.db = AsyncIOMotorClient(uri)[database]
    
    async def setup(self) -> None:
        logger.debug("Setting up database!")
        collection_names = await self.db.list_collection_names()
        if "Market" not in collection_names:
            logger.info("Creating Market collection!")
            market_collection = await self.db.create_collection("Market")
            await market_collection.insert_one({"_id": 0, "count": 0})
        if "Roblox" not in collection_names:
            logger.info("Creating Roblox collection!")
            await self.db.create_collection("Roblox")
        if "Resources" not in collection_names:
            logger.info("Creating Resources collection!")
            resources_collection = await self.db.create_collection("Resources")
            await resources_collection.insert_one({"_id": 0, "count": 0})
        if "Info" not in collection_names:
            logger.info("Creating Info collection!")
            info_collection = await self.db.create_collection("Info")
            info_collection.insert_one({"_id": 0, "items": []})
            info_collection.insert_one({"_id": 1, "count": 0})
        if "Evaluation" not in collection_names:
            logger.info("Creating Evaluation collection!")
            await self.db.create_collection("Evaluation")
        if "Permissions" not in collection_names:
            logger.info("Creating Permissions collection!")
            await self.db.create_collection("Permissions")
        if "Tracking" not in collection_names:
            logger.info("Creating Tracking collection!")
            tracking_collection = await self.db.create_collection("Tracking")
            await tracking_collection.insert_one({"_id": 0, "count": 0})

    async def validate_timestamp(self, market_data: dict) -> dict:
        logger.debug("Validating timestamp!")
        market_data["time_scanned"] = market_data["time_scanned"].replace(tzinfo=timezone.utc)
        return market_data

    async def insert_roblox_users_to_market(self, market_data: dict, roblox_users: Optional[dict] = None) -> None:
        """Insert Roblox Users into the market data.
        
        This function will replace the Vendor ID with a Roblox User Object instead of the ID.
        """
        if roblox_users is None:
            roblox_users = {doc["_id"]: doc async for doc in self.db["Roblox"].find()}

        logger.debug(f"Inserting Roblox users to market!")
        for value in market_data["items"].values():
            for listing in value["buy"]:
                try:
                    listing[2] = roblox_users[listing[2]]
                except KeyError:
                    logger.warning(f"User not found in database: {listing[2]}. Removing from output!")
                    value["buy"].remove(listing)
            for listing in value["sell"]:
                try:
                    listing[2] = roblox_users[listing[2]]
                except KeyError:
                    logger.warning(f"User not found in database: {listing[2]}. Removing from output!")
                    value["sell"].remove(listing)
        logger.debug(f"Completed: {market_data}")
        return market_data
    
    async def get_current_count(self) -> int:
        """Get the current count of market scans."""
        return (await self.db["Market"].find_one({"_id": 0}))["count"]
    
    async def get_market_at_index(self, index: int) -> MarketInstance:
        """Get the market at a specific index."""
        logger.debug(f"Getting market at index: {index}!")
        market = await self.db["Market"].find_one({"_id": index})

        # Inject Roblox Users into Market Data
        completed_market_data = await self.insert_roblox_users_to_market(market)

        # Validate Timestamp
        completed_market_data = await self.validate_timestamp(completed_market_data)

        return MarketInstance(**completed_market_data)

    async def get_current_market(self) -> MarketInstance:
        """Get the latest market scan."""
        logger.debug("Getting current market!")
        count = await self.get_current_count()

        market = await self.get_market_at_index(count)

        return market
    
    async def get_roblox_users(self) -> list[RobloxUser]:
        """Get all Roblox Users."""
        logger.debug("Getting all Roblox Users!")
        return [RobloxUser(**doc) async for doc in self.db["Roblox"].find()]

    async def get_current_market_for_user(self, user: RobloxUser) -> UserInstance:
        """Get the latest market scan for a user."""
        logger.debug(f"Getting current market for user: {user}!")

        market = await self.get_current_market()

        buy_listings = []
        sell_listings = []

        for item in market:
            for listing in item.buy:
                if listing.user == user:
                    buy_listings.append(listing)
            for listing in item.sell:
                if listing.user == user:
                    sell_listings.append(listing)

        
        return UserInstance(
            user=user,
            buy=buy_listings,
            sell=sell_listings
        )
    
    async def get_last_undercut_check(self) -> int:
        """Get the last undercut check."""
        logger.debug("Getting last undercut check!")
        return (await self.db["Info"].find_one({"_id": 1}))["count"]
        
    async def set_last_undercut_check(self, count: int) -> None:
        """Set the last undercut check."""
        logger.debug(f"Setting last undercut check to: {count}!")
        await self.db["Info"].update_one({"_id": 1}, {"$set": {"count": count}}, upsert=True)

    async def is_user_allowed_undercut(self, user_id: int) -> bool:
        """Check if a user is allowed to undercut."""
        logger.debug(f"Checking if user: {user_id} is allowed to undercut!")
        value = await self.db["Permissions"].find_one({"_id": user_id})
        return value is not None and value.get('permissions', {}).get("undercut", False)
    
    async def update_user_settings(self, user_id: int, tracked_id:int,  settings: TrackedUserMarketSettings) -> None:
        """Update a users settings."""
        logger.debug(f"Updating user settings for user: {user_id}!")
        await self.db["Permissions"].update_one(
            {"_id": user_id},
            {"$set": {f"tracked_users.{tracked_id}": settings.model_dump()}},
            upsert=True
        )

    async def get_users_settings(self, user: discord.User, bot: discord.Client, *, roblox_list: list[RobloxUser] = None) -> VioUser:
        """Get a users settings."""
        logger.debug(f"Getting user settings for user: {user.name}!")
        if roblox_list is None:
            roblox_list = await self.get_roblox_users()
        user_setting = await self.db["Permissions"].find_one({"_id": user.id}) or {}
        new_roblox_list = {
            next((i for i in roblox_list if i.id == int(roblox_id)), None): settings
            for roblox_id, settings in user_setting.get("tracked_users", {}).items() 
        }
        user_setting["tracked_users"] = new_roblox_list
        user_setting["discord_user"] = user
        return VioUser(**user_setting)
    
    async def get_users_tracked_accounts(self, bot: "Vio", roblox_list: list[RobloxUser] = None) -> list[VioUser]:
        """Get all users and their tracked accounts."""
        logger.debug("Getting all users and their tracked accounts!")
        users_permissions = []
        if roblox_list is None:
            roblox_list = await self.get_roblox_users()
        async for doc in self.db["Permissions"].find():
            user = bot.get_user(doc["_id"])
            if user is None:
                user = await bot.fetch_user(doc["_id"])
            user_setting = await self.db["Permissions"].find_one({"_id": user.id}) or {}
            new_roblox_list = {
                next((i for i in roblox_list if i.id == int(roblox_id)), None): settings
                for roblox_id, settings in user_setting.get("tracked_users", {}).items() 
            }
            user_setting["tracked_users"] = new_roblox_list
            user_setting["discord_user"] = user
            users_permissions.append(VioUser(**user_setting))
        return users_permissions
    
    async def is_user_tracking_account(self, user_id: int, account_id: int) -> bool:
        """Check if a user is tracking an account."""
        logger.debug(f"Checking if user: {user_id} is tracking account: {account_id}!")
        value = await self.db["Permissions"].find_one({"_id": user_id, f"tracked_users.{account_id}": {"$exists": True}})
        return value is not None
    
    async def add_tracked_account(self, user_id: int, account_id: int) -> None:
        """Add a tracked account to a user."""
        logger.debug(f"Adding tracked account: {account_id} to user: {user_id}!")
        await self.db["Permissions"].update_one(
            {"_id": user_id},
            {"$set": {f"tracked_users.{account_id}": {
                "undercut": True,
                "overcut": True,
                "completion": False,
                "new": False,
                "top_only": False,
                "market": {
                    "active": False,
                    "markets": []
                }
            }}}
        )

    async def remove_tracked_account(self, user_id: int, account_id: int) -> None:
        """Remove a tracked account from a user."""
        logger.debug(f"Removing tracked account: {account_id} from user: {user_id}!")
        await self.db["Permissions"].update_one(
            {"_id": user_id},
            {"$unset": {f"tracked_users.{account_id}": ""}}
        )

    async def get_latest_valid_market_for_item_before(self, count: int, item: str) -> MarketInstance:
        """Get the latest valid market for an item before a certain count."""
        logger.debug(f"Getting latest valid market for item: {item} before count: {count}!")

        market = await self.db["Market"].find_one({"_id": {"$lt": count}, f"items.{item}": {"$exists": True}}, sort=[("_id", -1)])
        if market is None:
            return None
        market = await self.insert_roblox_users_to_market(market)
        market = await self.validate_timestamp(market)


        return MarketInstance(**market)[item]

    async def get_item_history(self, item: str, *, depth: Optional[int] = None) -> MarketHistoryInstance:
        """Get the history of an item.
        
        Args:
            item (str): The item to get the history for.
            depth (Optional[int]): The depth to get the history for. Defaults to Complete History.
        """

        logger.debug(f"Getting item history: {item}!")

        async def process_document(document: dict, item_name: str, final_dict: dict, roblox: dict):
            """Process a document and add it to the final dict."""
            market_data = await self.insert_roblox_users_to_market(document, roblox)
            market_data = await self.validate_timestamp(market_data)

            item_instance = MarketInstance(**market_data)[item_name]

            final_dict[item_instance.id] = item_instance

        # Get all roblox users and store them in a dict so that we can use them for every document.
        # This is going to greatly reduce the amount of requests we make to the database.
        roblox_users = {doc["_id"]: doc async for doc in self.db["Roblox"].find()}

        # Create a dict to store all the item instances.
        item_instances = {}

        # Create a list of tasks to run.
        # This will allow us to run all the tasks at the same time.
        # This is going to greatly reduce the amount of time it takes to process all the data.
        tasks = []
        current_count = await self.get_current_count()
        async for doc in self.db["Market"].find(
            {"_id": {"$gt": current_count - depth if depth is not None else 0}},
            {"_id": 1, "time_scanned": 1, f"items.{item}": 1}):
            tasks.append(process_document(doc, item, item_instances, roblox_users))
        await asyncio.gather(*tasks)

        return MarketHistoryInstance(item_instances)

    async def get_item_list(self) -> list[str]:
        """Get a list of all items in the market."""
        logger.debug("Getting item list!")
        return list((await self.db["Info"].find_one({"_id": 0}))["items"])

    # Vio Testing

    async def is_user_allowed_evaluation(self, user_id: int) -> bool:
        """Check if a user is allowed to evaluate."""
        logger.info(f"Checking if user is allowed to evaluate: {user_id}!")
        perms = await self.db["Permissions"].find_one({"_id": user_id})
        if perms is None:
            return False
        return perms["evaluation"]

    async def upload_test_material(self, response: dict, orig_image: Image.Image, pros_image: Image.Image) -> None:
        """Upload test material to the database."""
        logger.debug("Uploading test material!")

        orig_img_bytes = BytesIO()
        orig_image.save(orig_img_bytes, format="PNG")
        orig_img_bytes.seek(0)

        pros_img_bytes = BytesIO()
        pros_image.save(pros_img_bytes, format="PNG")
        pros_img_bytes.seek(0)


        data = {
            "info": response,
            "image": orig_img_bytes.getvalue(),
            "processed": pros_img_bytes.getvalue()
        }

        await self.db["Evaluation"].insert_one(data)
    
    async def get_filtered_item_list(self, items: list[str]) -> dict[str, float]:
        """Get a list of all items in the market that match a filter."""
        logger.debug(f"Getting filtered item list: {items}!")

        roblox_users = {doc["_id"]: doc async for doc in self.db["Roblox"].find()}

        documents = {}
        for item in items:
            document = await self.db["Market"].find_one(
                {
                    "_id": {"$gt": 0},
                    f"items.{item}": {"$exists": True}
                }, {
                    "_id": 1,
                    "time_scanned": 1,
                    f"items.{item}": 1
                },
                sort=[("_id", -1)]
            )
            if document is None:
                documents[item] = None
                continue

            updated_document = await self.insert_roblox_users_to_market(document, roblox_users)
            updated_document = MarketInstance(**updated_document)

            item_instance = updated_document[item]

            value = None
            if item_instance.lowest_sell != 0:
                value = item_instance.lowest_sell
            elif item_instance.highest_buy != 0:
                value = item_instance.highest_buy
            else:
                value = None

            documents[item] = value
        return documents