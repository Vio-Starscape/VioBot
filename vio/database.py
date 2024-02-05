import asyncio
import aiohttp
import logging
from datetime import timezone
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from .marketinstance import MarketInstance
from .iteminstance import ItemInstance
from .changeinstance import MarketHistoryInstance

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
            await self.db.create_collection("Info")

    async def update_roblox_users_from_market(self, market_data: dict) -> None:
        logger.debug("Updating Roblox users from market! (Will be depricated!)")

        # Getting User IDs

        ids = set()
        for item in market_data["items"].values():
            for listing in item["buy"]:
                ids.add(listing[2])
            for listing in item["sell"]:
                ids.add(listing[2])

        existing_ids = {doc["_id"] async for doc in self.db["Roblox"].find({"_id": {"$in": list(ids)}})}
        ids -= existing_ids
        # Requesting User Data and updating DB (WILL BE MOVED TO LOAD BALANCER IN FUTURE!)
        async with aiohttp.ClientSession() as session:
            async with session.post("https://users.roblox.com/v1/users", json={"userIds": list(ids), "excludeBannedUsers": False}) as response:
                users = await response.json()
                logger.debug(f"Got users: {users}")
                for user in users["data"]:
                    logger.debug(f"Updating user: {user}")
                    await self.db["Roblox"].update_one({"_id": user["id"]}, {"$set": user}, upsert=True)

        logger.debug("Completed updating Roblox users from market!")

    async def validate_timestamp(self, market_data: dict) -> bool:
        logger.debug("Validating timestamp!")
        market_data["time_scanned"] = market_data["time_scanned"].replace(tzinfo=timezone.utc)
        return market_data

    async def insert_roblox_users_to_market(self, market_data: dict, roblox_users: Optional[dict] = None) -> None:
        """Insert Roblox Users into the market data.
        
        This function will replace the Vendor ID with a Roblox User Object instead of the ID.
        """

        # Will remove in future as writes should be done in the Load Balancer
        # await self.update_roblox_users_from_market(market_data)

        if roblox_users is None:
            roblox_users = {doc["_id"]: doc async for doc in self.db["Roblox"].find()}

        logger.debug("Inserting Roblox users to market!")
        for value in market_data["items"].values():
            for listing in value["buy"]:
                listing[2] = roblox_users[listing[2]]
            for listing in value["sell"]:
                listing[2] = roblox_users[listing[2]]
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
        count = (await self.get_current_count())-1

        market = await self.get_market_at_index(count)

        return market
    
    async def get_item_history(self, item: str) -> MarketHistoryInstance:
        """Get the history of an item."""
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
        async for doc in self.db["Market"].find(
            {"_id": {"$gt": 0}},
            {"_id": 1, "time_scanned": 1, f"items.{item}": 1}):
            tasks.append(process_document(doc, item, item_instances, roblox_users))
        await asyncio.gather(*tasks)

        return MarketHistoryInstance(item_instances)

    async def get_item_list(self) -> list[str]:
        """Get a list of all items in the market."""
        logger.debug("Getting item list!")
        return list((await self.db["Info"].find_one({"_id": 0}))["items"])