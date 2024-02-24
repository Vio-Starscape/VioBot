import discord
import logging
from fuzzywuzzy import process
from discord import app_commands
from discord.ext import commands
from main import Vio

from io import BytesIO
from PIL import Image, ImageDraw

from vio import get_info, get_item, modify_ratio

logger = logging.getLogger(__name__)

class Valuation(commands.Cog):

    def __init__(self, bot: Vio):
        self.bot = bot

    @app_commands.command()
    async def evaluation(self, interaction: discord.Interaction, inventory: discord.Attachment):
        """Get the valuation of your assets in inventory."""
        await interaction.response.defer(thinking=True)
        logger.info(f"Getting valuation of items. By: {interaction.user}")
        logger.info(f"Attachment: {inventory.filename}, {inventory.content_type}, {inventory.size}")
        if inventory.content_type != "image/png":
            await interaction.followup.send("I can only process PNG images!", ephemeral=True)
            return
        
        # Convert to an Image Object
        img_byte = BytesIO(await inventory.read())
        image = Image.open(img_byte)
        img_original = image.copy()
        img_draw = ImageDraw.Draw(image)

        item_names = await self.bot.db.get_item_list()

        response_dict = {
            "pre": [],
            "post": [],
            "prices": []
        }

        items_cache = {}

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
                    box[0] + config["name"][0] / w_scale,
                    box[1] + config["name"][1] / h_scale,
                    box[0] + config["name"][2] / w_scale,
                    box[1] + config["name"][3] / h_scale),
                    outline="blue")
                img_draw.rectangle((
                    box[0] + config["amount"][0] / w_scale,
                    box[1] + config["amount"][1] / h_scale,
                    box[0] + config["amount"][2] / w_scale,
                    box[1] + config["amount"][3] / h_scale), 
                    outline="green")

                name, amount = await get_info(img)
                if name.endswith("tag"):
                    continue
                
                response_dict["pre"].append((name, amount))

                pre_processed_names.append(name)
                name = process.extractOne(name, item_names)[0]
                response_dict["post"].append((name, int(amount or 0)))
                items_cache[name] = int(amount or 0)
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            await interaction.followup.send("I couldn't process that image! ;-;", ephemeral=True)

        if len(items_cache) == 0:
            await interaction.followup.send("I couldn't find any items in that image! ;-;", ephemeral=True)
            return
        
        print(items_cache)
        item_look = await self.bot.db.get_filtered_item_list(list(items_cache.keys()))
        print(item_look)

        valuation = discord.Embed(title="Your Item Valuation")

        item_str = ""

        total = 0
        for item, amount in items_cache.items():
            individual_price = item_look[item]
            if individual_price is None:
                response_dict["prices"].append((item, "Not Found", amount, "Not Found")) 
                item_str += f"{item} - Not Found\n"
                continue
            response_dict["prices"].append((item, individual_price, amount, individual_price * amount))
            total_price = individual_price * amount
            item_str += f"{item} - {amount:,} x {individual_price:,.2f} = {total_price:,.2f}\n"
            total += total_price

        valuation.add_field(name="Valuation", value=f"{total:,.2f}", inline=False)
        valuation.add_field(name="Items", value=item_str, inline=False)

        # valuation.add_field(name="Raw Names (Debugging)", value=f"\n".join(pre_processed_names), inline=True)
        valuation.set_image(url="attachment://img.png")

        buffered_format = BytesIO()
        image.save(buffered_format, format="PNG")
        buffered_format.seek(0)

        await self.bot.db.upload_test_material(
            response=response_dict,
            orig_image=img_original,
            pros_image=image
        )

        await interaction.followup.send(
            embed=valuation,
            file=discord.File(fp=buffered_format, filename="img.png")
        )


async def setup(bot: Vio):
    await bot.add_cog(Valuation(bot))