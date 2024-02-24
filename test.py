import time
import asyncio
import pprint
from vio import VioDB
from PIL import Image
from io import BytesIO

async def main():
    db = VioDB("mongodb://eric:Albert123@er-ic.ca/?authMechanism=DEFAULT", "TestVio")

    # async for doc in db.db["Evaluation"].find():
    #     processed = Image.open(BytesIO(doc["processed"]))
    #     processed.save("test.png")

    # items = ["Axnit", "Red Narcor", "Korrelite"]

    # def update(data, i):
    #     i_val = data["items"][i]
    #     i_val["_id"] = data["_id"]
    #     i_val["time_scanned"] = data["time_scanned"]
    #     return i_val

    # documents = []
    # for item in items:
    #     documents.append(
    #         update(await db.db["Market"].find_one(
    #             {
    #                 "_id": {"$gt": 0},
    #                 f"items.{item}": {"$exists": True}
    #             }, {
    #                 "_id": 1,
    #                 "time_scanned": 1,
    #                 f"items.{item}": 1
    #             },
    #             sort=[("_id", -1)]
    #         ), item)
    #     )

    # pprint.pprint(documents)

asyncio.run(main())