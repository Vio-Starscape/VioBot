import discord
import logging
import os
from discord.ext import commands
from vio import VioDB
from dotenv import load_dotenv
load_dotenv(override=True)

logger = logging.getLogger("VIO")

class Vio(commands.Bot):

    def __init__(self, db_uri: str, database: str):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=discord.Intents.default()
        )
        self.db = VioDB(db_uri, database)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info(f"Connected to {len(self.guilds)} guilds!")
        logger.info("-"*20)
        for guild in sorted(self.guilds, key=lambda g: g.me.joined_at):
            logger.info(f"\t{guild.name} (ID: {guild.id})")
        logger.info("-"*20)

    async def setup_hook(self) -> None:
        await self.db.setup()
        self.items = await self.db.get_item_list()
        self.roblox_users = await self.db.get_roblox_users()
        await self.load_extension("ext.Market")
        # await self.load_extension("ext.Valuation")

        # Testing
        # guild = discord.Object(id=971952765955895317)
        # self.tree.copy_global_to(guild=guild)
        # self.tree.clear_commands(guild=guild)
        # await self.tree.sync(guild=guild)
        await self.tree.sync()


if __name__ == "__main__":
    vio = Vio(os.getenv("MOTOR_URI"), os.getenv("DATABASE"))
    vio.run(
        os.getenv("BOT_TOKEN"), 
        root_logger=True,
        log_level=logging.INFO
    )