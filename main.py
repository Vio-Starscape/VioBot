import discord
import logging
import os
from datetime import datetime
from discord.ext import commands
from discord.ext import tasks
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
        self.up_time = datetime.now()

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
        await self.load_extension("ext.Valuation")

        # Testing
        # guild = discord.Object(id=os.getenv("MAIN_GUILD_ID"))
        # self.tree.copy_global_to(guild=guild)
        # self.tree.clear_commands(guild=guild)
        # await self.tree.sync(guild=guild)
        await self.tree.sync()

    @tasks.loop(minutes=10)
    async def update(self):
        """Update task

        This task will update the items and roblox users every 10 minutes.
        This can also be used for other tasks such as undercut pings
        """
        self.items = await self.db.get_item_list()
        self.roblox_users = await self.db.get_roblox_users()

vio = Vio(os.getenv("MOTOR_URI"), os.getenv("DATABASE"))

@vio.tree.command()
async def stats(interaction: discord.Interaction):

    embed = discord.Embed(
        title="General Information",
        description="Here is some general information regarding Vio. Created by `Meaning`",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="Uptime",
        value="Given an image of your inventory, I will evaluate the value of your items."
    )
    embed.add_field(
        name="Guilds",
        value=len(vio.guilds)
    )
    embed.set_footer(
        text="Version: 1.18b"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    vio.run(
        os.getenv("BOT_TOKEN"), 
        root_logger=True,
        log_level=logging.INFO
    )