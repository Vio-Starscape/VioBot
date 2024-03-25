import discord
import numpy as np
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Optional, Tuple

from .listing import Listing, ListingType
from .marketchanges import MarketChangeType
from .robloxuser import RobloxUser

class ItemInstance(BaseModel):
    id: int = Field(alias="_id")
    time_scanned: datetime
    name: str
    buy: List[Listing]
    sell: List[Listing]

    @validator('buy', pre=True, always=True)
    def sort_buy_listings(cls, v, values):
        name = values.get('name')
        for listing in v:
            listing.append(ListingType.BUY)
            listing.append(name)
        return v
    
    @validator('sell', pre=True, always=True)
    def sort_sell_listings(cls, v, values):
        name = values.get('name')
        for listing in v:
            listing.append(ListingType.SELL)
            listing.append(name)
        return v
    
    def process_changes(self, initial_instance: "ItemInstance", previous_instance: "ItemInstance") -> Tuple[
            List[Tuple[MarketChangeType, Optional[float], Optional[int], Optional[RobloxUser]]],
            List[Tuple[MarketChangeType, Optional[float], Optional[int], Optional[RobloxUser]]]
                ]:
        """Process the changes between two instances."""
        buy_changes = []
        sell_changes = []

        initial_buy = {listing.user.id: listing for listing in initial_instance.buy}
        previous_buy = {listing.user.id: listing for listing in previous_instance.buy}

        initial_sell = {listing.user.id: listing for listing in initial_instance.sell}
        previous_sell = {listing.user.id: listing for listing in previous_instance.sell}

        # Process the Buy changes
        for listing in initial_instance.buy:
            matching_listing = previous_buy.get(listing.user.id)
            if matching_listing:
                if matching_listing.price == listing.price and matching_listing.amount == listing.amount:
                    pass
                elif matching_listing.price == listing.price and matching_listing.amount > listing.amount:
                    buy_changes.append([MarketChangeType.SOLD, listing.price, matching_listing.amount - listing.amount, listing.user])
                else:
                    buy_changes.append([MarketChangeType.NEW, listing.price, listing.amount, listing.user])
            else:
                buy_changes.append([MarketChangeType.NEW, listing.price, listing.amount, listing.user])
        for listing in previous_instance.buy:
            if initial_buy.get(listing.user.id) is None:
                buy_changes.append([MarketChangeType.COMPLETED, listing.price, listing.amount, listing.user])

        # Process the Sell changes
        for listing in initial_instance.sell:
            matching_listing = previous_sell.get(listing.user.id)
            if matching_listing:
                if matching_listing.price == listing.price and matching_listing.amount == listing.amount:
                    pass
                elif matching_listing.price == listing.price and matching_listing.amount > listing.amount:
                    sell_changes.append([MarketChangeType.SOLD, listing.price, matching_listing.amount - listing.amount, listing.user])
                else:
                    sell_changes.append([MarketChangeType.NEW, listing.price, listing.amount, listing.user])
            else:
                sell_changes.append([MarketChangeType.NEW, listing.price, listing.amount, listing.user])
        for listing in previous_instance.sell:
            if initial_sell.get(listing.user.id) is None:
                sell_changes.append([MarketChangeType.COMPLETED, listing.price, listing.amount, listing.user])

        return sell_changes, buy_changes
            
    
    def __sub__(self, other: "ItemInstance") -> Tuple[
            List[Tuple[MarketChangeType, Optional[float], Optional[int], Optional[RobloxUser]]],
            List[Tuple[MarketChangeType, Optional[float], Optional[int], Optional[RobloxUser]]]
                ]:
        if not isinstance(other, ItemInstance):
            raise TypeError("Can only subtract ItemInstances from ItemInstances!")

        if other == self:
            raise ValueError("Cannot subtract the same instance from itself!")
        
        if other.id > self.id: # If the other instance is newer than this one
            return self.process_changes(other, self)
        else:
            return self.process_changes(self, other)
        
    @property
    def valid(self):
        return len(self.buy) > 0 or len(self.sell) > 0
                
    @property
    def buy_volume(self):
        return sum([listing.amount for listing in self.buy])
    
    @property
    def sell_volume(self):
        return sum([listing.amount for listing in self.sell])
    
    @property
    def volume(self):
        return self.buy_volume + self.sell_volume

    @property
    def lowest_sell(self):
        return min([listing.price for listing in self.sell]) if len(self.sell) > 0 else 0
    
    @property
    def average_sell(self) -> float:
        if len(self.sell) == 0: return 0

        # THIS IS THE KEVIN METHOD TO GET RID OF STARSCAPE OUTLIERS
        i = 0
        for listing in self.sell:
            i += listing.price * listing.amount
        average = i / self.sell_volume

        unoutlierd = [i for i in [listing.price for listing in self.sell] if i < average * 2]

        return round(float(np.average(unoutlierd)), 2)
    
    @property
    def highest_buy(self):
        return max([listing.price for listing in self.buy]) if len(self.buy) > 0 else 0
    
    @property
    def average_buy(self) -> float:
        if len(self.buy) == 0: return 0

        # THIS IS THE KEVIN METHOD TO GET RID OF STARSCAPE OUTLIERS
        i = 0
        for listing in self.buy:
            i += listing.price * listing.amount
        average = i / self.buy_volume

        unoutlierd = [i for i in [listing.price for listing in self.sell] if i < average * 2]

        return round(float(np.average(unoutlierd)), 2)
    
    @property
    def embed(self):
        item_embed = discord.Embed(title=self.name, color=0x808080)

        item_embed.add_field(name="Best Sell Price", value=f"{self.lowest_sell:,.2f}", inline=True)
        item_embed.add_field(name="Volume", value=f"{self.sell_volume:,}/{self.buy_volume:,}", inline=True)
        item_embed.add_field(name="Best Buy Price", value=f"{self.highest_buy:,.2f}", inline=True)

        if len(self.sell) == 0:
            item_embed.add_field(name="Sell Listings", value="No sell listings.", inline=True)
        else:
            sell_listings_str = "\n".join([f"{listing.amount:,} @ {listing.price:,.2f} by [{listing.user.name}]({listing.user.roblox_tiny_profile})" for listing in self.sell])
            if len(sell_listings_str) > 1024:
                sell_listings_str = "\n".join([f"{listing.amount:,} @ {listing.price:,.2f} by **{listing.user.name}**" for listing in self.sell])
            item_embed.add_field(name="Sell Listings", value=sell_listings_str, inline=True)

        if len(self.buy) == 0:
            item_embed.add_field(name="Buy Listings", value="No buy listings.", inline=True)
        else:
            buy_listings_str = "\n".join([f"{listing.amount:,} @ {listing.price:,.2f} by [{listing.user.name}]({listing.user.roblox_tiny_profile})" for listing in self.buy])
            if len(buy_listings_str) > 1024:
                buy_listings_str = "\n".join([f"{listing.amount:,} @ {listing.price:,.2f} by **{listing.user.name}**" for listing in self.buy])

            item_embed.add_field(name="Buy Listings", value=buy_listings_str, inline=True)

        item_embed.set_footer(text="Provided by Vio")
        item_embed.timestamp = self.time_scanned

        return item_embed
