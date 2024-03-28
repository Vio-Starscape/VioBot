import discord

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import Vio

class AffiliationModal(discord.ui.Modal):
    name = discord.ui.TextInput(
        label="Title",
        placeholder="XYZ Technological Division"
    )
    url = discord.ui.TextInput(
        label="Affiliation URL",
        placeholder="https://discord.gg/YURXDmxYYn"
    )
    thumb_url = discord.ui.TextInput(
        label="Affiliation Thumbnail URL",
        placeholder="https://i.imgur.com/poopy.png"
    )
    about = discord.ui.TextInput(
        label="About",
        style=discord.TextStyle.paragraph,
        placeholder="Affiliation Description",
    )

    def __init__(self, bot: "Vio"):
        self.bot = bot
        super().__init__(title="Affiliation Form")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel = await interaction.guild.fetch_channel(self.bot.affiliation_channel)

        aff_embed = discord.Embed(
            title=self.name.value,
            url=self.url.value,
            description=self.about.value
        )
        aff_embed.set_thumbnail(url=self.thumb_url.value)
        aff_embed.timestamp = discord.utils.utcnow()

        await channel.send(embed=aff_embed)
        await interaction.response.send_message("Affiliation submitted!", embed=aff_embed, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message("Affiliation submission failed!, Contact Meaning#0001 or read the error!\n```{}```".format(str(error)), ephemeral=True)