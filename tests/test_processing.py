import unittest
import json
import os
import cv2
import numpy as np
import pytesseract
from io import BytesIO
from PIL import Image
from vio.processing import get_item, get_info, modify_ratio, process_image, preprocess_amount, preprocess_title

class TestOCR(unittest.TestCase):

    # def setUp(self) -> None:
    #     self.loop = asyncio.get_event_loop()
    #     asyncio.set_event_loop(None)

    # def tearDown(self) -> None:
    #     self.loop.close()
    #     self.loop = None

    def test_ocr(self):
        for i in filter(lambda x: x.endswith(".png"), os.listdir('tests/images')):
            image = Image.open(f"tests/images/{i}")
            boxes = get_item(image)
            response = json.loads(open(f'tests/images/{i.replace(".png", ".json")}').read())
            data = []
            imgs = {}
            for box in boxes:
                img = image.crop(box)
                img, _ = modify_ratio(img)
                processed_img_amount = preprocess_amount(process_image(img, (340, 15, 381, 34)))
                processed_img_name = preprocess_title(process_image(img, (35, 0, 250, 20)))

                name, amount = get_info(img)
                print(f"{name}: {amount = }")
                imgs[name] = [processed_img_name, processed_img_amount]
                try:
                    data.append([name, int(amount if amount else 0)])
                except ValueError:
                    Image.fromarray(processed_img_amount).save("error.png")
                    raise

            for x, y in zip(data, response):
                try:
                    self.assertEquals(x, y)
                except AssertionError:
                    Image.fromarray(imgs[x[0]][0]).save("error.png")
                    Image.fromarray(imgs[x[0]][1]).save("error2.png")
                    raise

if __name__ == "__main__":
    unittest.main()