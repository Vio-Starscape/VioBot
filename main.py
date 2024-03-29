import discord
import logging
import os
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
        self.main_guild = discord.Object(id=int(os.getenv("MAIN_GUILD_ID")))
        self.affiliation_channel = int(os.getenv("AFFILIATION_CHANNEL"))
        self.testing = os.getenv("TESTING") == "True"
        self.db = VioDB(db_uri, database)
        self.up_time = discord.utils.utcnow()

    async def on_ready(self):
        await self.change_presence(
            activity=discord.Activity(
                name="the market!",
                type=discord.ActivityType.watching
            )
        )

        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info(f"Connected to {len(self.guilds)} guilds!")
        logger.info("-"*20)
        for guild in sorted(self.guilds, key=lambda g: g.me.joined_at):
            logger.info(f"\t{guild.name} (ID: {guild.id})")
        logger.info("-"*20)

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="market changes!"
            )
        )

    async def setup_hook(self) -> None:
        await self.db.setup()
        self.items = await self.db.get_item_list()
        self.roblox_users = await self.db.get_roblox_users()
        await self.load_extension("ext.Market")
        await self.load_extension("ext.Valuation")
        await self.load_extension("ext.VioExclusive")
        if not self.testing: # Do not want to start pinging people if I am just testing with Prod DB (Testing DB does not have up to date stats)
            await self.load_extension("ext.Undercut")
        await self.tree.sync()
        await self.tree.sync(guild=self.main_guild)

        self.update.start()

    @tasks.loop(minutes=10)
    async def update(self):
        """Update task

        This task will update the items and roblox users every 10 minutes.
        This can also be used for other tasks such as undercut pings
        """
        self.items = await self.db.get_item_list()
        self.roblox_users = await self.db.get_roblox_users()

vio = Vio(os.getenv("MOTOR_URI"), os.getenv("DATABASE"))

@vio.tree.command(
    description="Get general information about the bot."
)
async def stats(interaction: discord.Interaction):
    logger.info(f"Status Invoked | By: {interaction.user} | "
            f"In: {interaction.guild.name if interaction.guild else interaction.channel.recipient.name}"
            f" (ID: {interaction.guild.id if interaction.guild else interaction.channel.id})")

    embed = discord.Embed(
        title="General Information",
        description="Here is some general information regarding Vio.\nCreated by `Meaning`",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="Uptime",
        value=f"{discord.utils.format_dt(vio.up_time, 'R')}"
    )
    embed.add_field(
        name="Guilds",
        value=f"Count: {len(vio.guilds)}"
    )
    embed.set_footer(
        text=f"Version: {os.getenv('VERSION')}"
    )
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    vio.run(
        os.getenv("BOT_TOKEN"), 
        root_logger=True,
        log_level=logging.INFO
    )