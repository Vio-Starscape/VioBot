import discord
import logging
from fuzzywuzzy import process
from discord import app_commands
from discord.ext import commands
from main import Vio

from typing import Optional

from io import BytesIO
from PIL import Image, ImageDraw
from vio import get_info, get_item, modify_ratio

logger = logging.getLogger(__name__)

class Valuation(commands.Cog):

    def __init__(self, bot: Vio):
        self.bot = bot

    @app_commands.command(description="Given an image of your inventory, I will evaluate the value of your items.")
    @app_commands.describe(flex="Whether or not you want to flex your wealth.", processed_images="Whether or not you want to see the processed images.")
    async def evaluation(self, 
                         interaction: discord.Interaction,
                         image1: discord.Attachment, 
                         image2: Optional[discord.Attachment] = None,
                         image3: Optional[discord.Attachment] = None,
                         image4: Optional[discord.Attachment] = None,
                         image5: Optional[discord.Attachment] = None,
                         image6: Optional[discord.Attachment] = None,
                         image7: Optional[discord.Attachment] = None,
                         image8: Optional[discord.Attachment] = None,
                         image9: Optional[discord.Attachment] = None,
                         flex: Optional[bool] = False,
                         processed_images: Optional[bool] = False
                         ):
        """Get the valuation of your assets in inventory."""
        images: list[discord.Attachment] = [i for i in 
                  [image1, image2, image3, image4, image5, image6, image7, image8, image9]
                  if i is not None]

        # if not await self.bot.db.is_user_allowed_evaluation(interaction.user.id):
        #     logger.info(f"User {interaction.user} tried to use the evaluation command, but does not have access.")
        #     await interaction.response.send_message(
        #         "You are not allowed to use this command!\n\n"
        #         "If you would like access to this command DM meaning from [Vio](https://discord.gg/3dUWakkSyj)\n"
        #         "Though it is in beta, Price is going to be 100k for lifetime access to the evaluation command.\n"
        #         "This will transfer to any future project involving the evaluation of assets.", ephemeral=True)
        #     return

        await interaction.response.defer(thinking=True, ephemeral=(not flex))
        logger.info(f"Getting valuation of items. By: {interaction.user} | "
                    f"In: {interaction.guild.name if interaction.guild else interaction.channel.recipient.name} "
                    f" (ID: {interaction.guild.id if interaction.guild else interaction.channel.id})" +
                    "".join([f"\n\tAttachment: {inventory.filename}, {inventory.content_type}, {inventory.size}"
                             for inventory in images])
                    )

        item_names = await self.bot.db.get_item_list()

        total_asset_valuation = 0

        embeds = [
            discord.Embed(
                title="Valuation",
                description="This command is currently in Beta. All images are saved and used for future training. Some item names or Amount could be incorrect.",
                color=0xFF0000
            )
        ]
        image_files = []
        for i, inventory in enumerate(images, start=1):
            if inventory.content_type not in ["image/png"]:
                embeds.append(discord.Embed(
                    title=f"Invalid Attachment for image{i}",
                    description="I can only process images in PNG format!",
                    color=0xFF0000
                ))
                continue
            # Convert to an Image Object
            img_byte = BytesIO(await inventory.read())
            image = Image.open(img_byte)
            img_original = image.copy()
            img_draw = ImageDraw.Draw(image)

            response_dict = {
                "pre": [],
                "post": [],
                "prices": []
            }

            items_cache = []

            pre_processed_names = []

            config = {
                "name": (35, 0, 250, 20),
                "amount": (340, 15, 381, 34),
            }

            try:
                boxes = get_item(image)
                for box in boxes:
                    img_draw.rectangle(box, outline="red")
                    img, (w_scale, h_scale) = modify_ratio(image.crop(box))
                    img_draw.rectangle((
                        box[0] + config["name"][0] * w_scale,
                        box[1] + config["name"][1] * h_scale,
                        box[0] + config["name"][2] * w_scale,
                        box[1] + config["name"][3] * h_scale),
                        outline="blue")
                    img_draw.rectangle((
                        box[0] + config["amount"][0] * w_scale,
                        box[1] + config["amount"][1] * h_scale,
                        box[0] + config["amount"][2] * w_scale,
                        box[1] + config["amount"][3] * h_scale), 
                        outline="green")

                    name, amount = await get_info(img)
                    if name.endswith("tag"):
                        continue
                    
                    response_dict["pre"].append((name, amount))

                    pre_processed_names.append(name)
                    name = process.extractOne(name, item_names)[0]
                    response_dict["post"].append((name, int(amount or 0)))
                    items_cache.append([name, int(amount or 0)])
            except Exception as e:
                logger.error(f"Error processing image: {e}")
                embeds.append(discord.Embed(
                    title=f"Error Processing Image {i}",
                    description="I couldn't process that image!\n Make sure the full window is in view, and that you are in **List** view.",
                    color=0xFF0000
                ))
                continue

            if len(items_cache) == 0:
                embeds.append(discord.Embed(
                    title=f"Error Processing Image {i}",
                    description="I couldn't process that image!\n Make sure the full window is in view, and that you are in **List** view.",
                    color=0xFF0000
                ))
                continue
            item_look = await self.bot.db.get_filtered_item_list([i[0] for i in items_cache])

            valuation = discord.Embed(title=f"Image {i} Valuation", color=0x808080)

            item_str = ""

            total = 0
            logger.info(f"Items Cache: {items_cache}")
            for item, amount in [tuple(i) for i in items_cache]:
                individual_price = item_look[item]
                if individual_price is None:
                    response_dict["prices"].append((item, "Not Found", amount, "Not Found")) 
                    item_str += f"{item} - Not Found\n"
                    continue
                response_dict["prices"].append((item, individual_price, amount, individual_price * amount))
                total_price = individual_price * amount
                item_str += f"{item} - {amount:,} x {individual_price:,.2f} = {total_price:,.2f}\n"
                total += total_price

            total_asset_valuation += total
            valuation.add_field(name="Valuation", value=f"{total:,.2f}", inline=False)
            valuation.add_field(name="Items", value=item_str, inline=False)

            # valuation.add_field(name="Raw Names (Debugging)", value=f"\n".join(pre_processed_names), inline=True)
            if processed_images:
                valuation.set_image(url=f"attachment://img{i}.png")

            buffered_format = BytesIO()
            image.save(buffered_format, format="PNG")
            buffered_format.seek(0)

            await self.bot.db.upload_test_material(
                response=response_dict,
                orig_image=img_original,
                pros_image=image
            )

            if processed_images:
                image_files.append(discord.File(fp=buffered_format, filename=f"img{i}.png"))
            embeds.append(valuation)

        embeds[0].add_field(name="Total Valuation", value=f"{total_asset_valuation:,.2f}", inline=False)

        await interaction.followup.send(
            embeds=embeds,
            ephemeral=(not flex),
            files=image_files
        )


async def setup(bot: Vio):
    await bot.add_cog(Valuation(bot))