from PIL import Image
from scipy import stats
from io import BytesIO
import aiopytesseract
import re
import numpy as np
import cv2

CONFIG = {
    "name": (35, 0, 250, 20),
    "amount": (340, 15, 381, 34),
}

def extract_region(image_object: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray:
    return image_object[region[1]: region[3], region[0]: region[2]]

def process_image(img: Image.Image, region: tuple[int, int, int, int]) -> np.ndarray:
    img = np.array(img)
    img = extract_region(img, region)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    img = cv2.bitwise_not(img)
    img = cv2.resize(img, None, fx=5, fy=5, interpolation=cv2.INTER_LINEAR)
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

async def get_info(img: Image.Image) -> tuple[str, str]:
    name = await get_title(process_image(img, CONFIG["name"]))
    amount = await get_amount(process_image(img, CONFIG["amount"]))
    return name, amount

def fix_title(title: str):
    # Hide this from the light of DAY
    # title = text_striping(title)
    # title = title.replace("Oread", "Dread")
    title = title.replace("Orone", "Drone")
    # title = title.replace("LGS", "LG5")
    # title = title.replace("x9", "X9")
    # title = re.sub(r'\s(?:I|T|L|f|l|1){1,3}(?=\s|$)',
    #                 lambda match: match.group(0)
    #                     .replace('T', 'I')
    #                     .replace('L', 'I')
    #                     .replace('l', 'I')
    #                     .replace('1', 'I')
    #                     .replace('f', 'I'),
    #                 title)
    return title.strip()

def preprocess_title(img: np.ndarray) -> np.ndarray:
    # img = cv2.resize(img, None, fx=1.2, fy=1, interpolation=cv2.INTER_CUBIC)
    # kern = np.ones((5, 5), np.uint8)
    # img = cv2.GaussianBlur(img, (1, 1), 2)

    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((1, 1), np.uint8), iterations=1)
    img = cv2.resize(img, None, fx=1.1, fy=1, interpolation=cv2.INTER_CUBIC)
    img = cv2.morphologyEx(img, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8), iterations=1)
    # img = cv2.dilate(img, np.ones((4, 1), np.uint8), iterations=1)
    # img = cv2.detailEnhance(img, sigma_s=10, sigma_r=0.15)
    # img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    # img = cv2.erode(img, np.ones((2, 0), np.uint8), iterations=1)
    return img

async def get_title(img: np.ndarray):
    img = preprocess_title(img)

    buff = BytesIO()
    Image.fromarray(img).save(buff, format="PNG")
    buff.seek(0)

    output = await aiopytesseract.image_to_string(
        buff.getvalue(),
        # lang="model",
        psm=10,
        # oem=1,
        # tessdata_dir="./tessdata",
        config=[
            ("tessedit_char_blacklist", "$[]")
        ]
    )

    # output = pytesseract.image_to_string(
    #     img,
    #     lang="model",
    #     config="--psm 10"
    #     " --oem 1"
    #     " --tessdata-dir ./tessdata"
    #     " -c tessedit_char_blacklist=$[]"
    # )
    return fix_title(output)

def preprocess_amount(img: np.ndarray) -> np.ndarray:
    img = cv2.resize(img, None, fx=2.1, fy=2, interpolation=cv2.INTER_CUBIC)
    # img = cv2.threshold(cv2.medianBlur(img, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # img = cv2.GaussianBlur(img, (3, 3), 2)
    # img = cv2.Canny(img, 50, 150)
    # kernel = np.array([[0, -1, 0],
    #                [-1, 5,-1],
    #                [0, -1, 0]])

    # # Apply the kernel to the image
    # # img = cv2.dilate(img, np.ones((3, 2), np.uint8), iterations=1)
    # # _, img = cv2.threshold(img, 100, 255, cv2.THRESH_BINARY)
    # img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)
    img = cv2.morphologyEx(img, cv2.MORPH_OPEN, np.ones((3, 1), np.uint8), iterations=1)

    img = cv2.dilate(img, np.ones((0, 1), np.uint8), iterations=1)
    # img = cv2.filter2D(img, -1, kernel)
    img = cv2.GaussianBlur(img, (5, 3), 0)
    _, img = cv2.threshold(img, 40, 255, cv2.THRESH_BINARY)
    img = cv2.dilate(img, np.ones((1, 2), np.uint8), iterations=1)
    img = cv2.erode(img, np.ones((3, 3), np.uint8), iterations=1)
    return img

async def get_amount(img: np.ndarray):
    img = preprocess_amount(img)

    buff = BytesIO()
    Image.fromarray(img).save(buff, format="PNG")
    buff.seek(0)

    output = await aiopytesseract.image_to_string(
        buff.getvalue(),
        # lang="model",
        psm=10,
        # oem=1,
        # tessdata_dir="./tessdata",
        config=[
            ("tessedit_char_blacklist", "$[]")
        ]
    )

    # output = pytesseract.image_to_string(img,
    #     lang="model",
    #     config="--psm 10"
    #     " --oem 1"
    #     ' -c tessedit_char_blacklist="$[]/"'
    #     " --tessdata-dir ./tessdata"
    #     )
    # print(output.strip())
    # if output.strip() == "":
    #     print("Here")
    #     output = pytesseract.image_to_string(img,
    #         lang="eng",
    #         config="--psm 10"
    #         " --oem 1"
    #         ' -c tessedit_char_blacklist="$[]/"'
    #         " --tessdata-dir ./tessdata"
    #         )
    #     print(output.strip())
    if output.strip().endswith("ed"): return 0
    text = text_striping(output)
    # text = text.replace("?", "1").replace("s", "5").replace("S", "5").replace("g", "9").replace("]", "1")
    return text.strip()

def get_item(image: Image.Image) -> list[tuple[int, int, int, int]]:
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
        # Only if it matches the mode width and height with margin of error
        diff_w, diff_h = w - mode_width, h - mode_height
        if 0 <= diff_w <= 5 and 0 <= diff_h <= 5:
            boxes.append((x+(diff_w//2), y+(diff_h//2), x+w+(diff_w//2), y+h+(diff_h//2)))
    
    return sorted(boxes, key=lambda x: x[1])