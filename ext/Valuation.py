import discord
import logging
from fuzzywuzzy import process
from discord import app_commands
from discord.ext import commands
from main import Vio

from typing import Optional

from io import BytesIO
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

import aiopytesseract
from PIL import Image
from scipy import stats
from io import BytesIO
import re
import numpy as np
import cv2

CONFIG = {
    "name": (35, 0, 250, 20),
    "amount": (340, 15, 381, 34),
}

def extract_region(image_object: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray:
    return image_object[region[1]: region[3], region[0]: region[2]]

def process_image(img: Image, region: tuple[int, int, int, int], amount: bool = False) -> np.ndarray:
    img = np.array(img)
    img = extract_region(img, region)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    img = cv2.bitwise_not(img)
    img = cv2.resize(img, None, fx=5 if amount else 4, fy=5 if amount else 4, interpolation=cv2.INTER_CUBIC)
    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return img

def modify_ratio(image: Image.Image) -> tuple[Image.Image, tuple[float, float]]:
    w, h = image.size
    new_w, new_h = 381, 34

    w_scale = w / new_w
    h_scale = h / new_h
    return image.resize((381, 34)), (w_scale, h_scale)

def text_striping(text: str):
    text = text.strip("\n ")
    text = re.sub(r"\n[\s]+", "\n", text)
    text = re.sub(r"\n?Station|[\s]+$", "", text)
    return text

async def get_info(img: Image):
    name = await get_title(process_image(img, CONFIG["name"], amount=False))
    amount = await get_amount(process_image(img, CONFIG["amount"], amount=True))
    return (name, amount)

async def get_title(img: np.ndarray):
    buffer = BytesIO()
    Image.fromarray(img).save(buffer, format="PNG")
    output = await aiopytesseract.image_to_string(
        buffer.getvalue(), 
        psm=7)
    text = text_striping(output)
    return text.strip()

async def get_amount(img: np.ndarray):
    buffer = BytesIO()
    Image.fromarray(img).save(buffer, format="PNG")
    output = await aiopytesseract.image_to_string(
        buffer.getvalue(), 
        psm=7,
        config=[('tessedit_char_whitelist', '0123456789,.')])
    text = text_striping(output)
    text = re.sub(r"[, ]", "", text)
    return text.strip()

def get_item(image: Image) -> list[tuple[int, int, int, int]]:
    img = np.array(image)

    # Change Background to white
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    to_change = np.array([30, 30, 30])
    to_color = np.array([255, 255, 255])
    img[np.where((img == to_change).all(axis=2))] = to_color

    # Get boxes
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Get mode of boxes width and height
    widths = []
    heights = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Only if the width is bigger than the height
        if w > h and w > 10 and h > 10:
            widths.append(w)
            heights.append(h)
    mode_width = stats.mode(widths)[0]
    mode_height = stats.mode(heights)[0]

    boxes: list[tuple[int, int, int, int]] = []
    # return boxes coords with the mode width and height
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w == mode_width and h == mode_height:
            boxes.append((x, y, x+w, y+h))
    
    return boxes



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

        if not await self.bot.db.is_user_allowed_evaluation(interaction.user.id):
            logger.info(f"User {interaction.user} tried to use the evaluation command, but does not have access.")
            await interaction.response.send_message(
                "You are not allowed to use this command!\n\n"
                "If you would like access to this command DM meaning from [Vio](https://discord.gg/3dUWakkSyj)\n"
                "Though it is in beta, Price is going to be 100k for lifetime access to the evaluation command.\n"
                "This will transfer to any future project involving the evaluation of assets.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=(not flex))
        logger.info(f"Getting valuation of items. By: {interaction.user} | In: {interaction.guild.name} (ID: {interaction.guild.id})" +
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
            if inventory.content_type not in ["image/png", "image/jpeg"]:
                embeds.append(discord.Embed(
                    title=f"Invalid Attachment for image{i}",
                    description="I can only process images in PNG or JPEG format!",
                    color=0xFF0000
                ))
                return
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
                    items_cache[name] = int(amount or 0)
            except Exception as e:
                logger.error(f"Error processing image: {e}")
                await interaction.followup.send("I couldn't process that image! ;-;", ephemeral=True)

            if len(items_cache) == 0:
                await interaction.followup.send("I couldn't find any items in that image! ;-;", ephemeral=True)
                return
            item_look = await self.bot.db.get_filtered_item_list(list(items_cache.keys()))

            valuation = discord.Embed(title=f"Image {i} Valuation", color=0x808080)

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