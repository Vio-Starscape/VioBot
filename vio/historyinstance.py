import discord
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
from io import BytesIO
from enum import Enum
from typing import Dict

from .marketchanges import MarketChangeType
from .iteminstance import ItemInstance

class MarketHistoryInstance:

    def __init__(self, item_instances: Dict[int, ItemInstance]):
        self.item_instances = item_instances
        self.max_page = max(item_instances.keys())
        self.min_page = min(item_instances.keys())
        self.name = item_instances[self.max_page].name

    def __getitem__(self, key: int) -> ItemInstance:
        return self.item_instances[key]
    
    async def process_changes(self, initial_instance: ItemInstance, previous_instance: ItemInstance) -> MarketChangeType:
        """Process the changes between two instances."""
    
    async def changes_for(self, page: int) -> discord.Embed:
        """Get the changes for a specific page."""
        if page < (self.min_page+1) or page > self.max_page:
            raise ValueError("Page out of range!")
        
        # Get the instances
        instance1 = self.item_instances[page]
        instance2 = self.item_instances[page - 1]

        # Process the changes
        sell_changes, buy_changes = instance1 - instance2

        def changes_to_string(listing: list):
            if listing[0] == MarketChangeType.NEW:
                return f"New listing for {listing[2]:,} at {listing[1]:,.2f} by **{listing[3].name}**"
            elif listing[0] == MarketChangeType.SOLD:
                return f"{listing[3].name} fulfilled {listing[2]:,} at {listing[1]:,.2f}"
            elif listing[0] == MarketChangeType.COMPLETED:
                return f"{listing[3].name} fulfilled {listing[2]:,} at {listing[1]:,.2f} completing the listing!"

        change_embed = discord.Embed(
            title=f"Market Change for {self.name}",
            color=discord.Color.blurple()
        )

        if len(sell_changes) > 0:
            change_embed.add_field(
                name="Sell Changes",
                value="\n".join([changes_to_string(change) for change in sell_changes])
            )
        else:
            change_embed.add_field(
                name="Sell Changes",
                value="No changes."
            )

        if len(buy_changes) > 0:
            change_embed.add_field(
                name="Buy Changes",
                value="\n".join([changes_to_string(change) for change in buy_changes])
            )
        else:
            change_embed.add_field(
                name="Buy Changes",
                value="No changes."
            )

        change_embed.timestamp = discord.utils.utcnow()

        return change_embed
    
    @property
    def view(self) -> "MarketChangeView":
        return MarketChangeView(self)
    
    async def change_between_instances(self, page: int) -> discord.Embed:
        change_embed = discord.Embed(
            title=f"Market Change for {self.name} (Page {page})",
            color=discord.Color.blurple()
        )
    
    async def graph(self) -> discord.File:
        """Graph the entire recorded history of the item."""
        return await self.graph_between_pages(
            self.max_page-1000,
            self.max_page
        )
    

    async def graph_between_pages(self, page1: int, page2: int, iqr: bool = True) -> discord.File:
        """Graph the difference between two pages."""
        if page1 > page2:
            page1, page2 = page2, page1
        if page1 < self.min_page:
            page1 = self.min_page
        if page2 > self.max_page:
            page2 = self.max_page

        def interQuartileRange(data: list):
            Q1, Q3 = np.percentile([d for d in data if d is not None], [10, 90])
            IQR = Q3 - Q1
            
            info = []
            for point in data:
                if point is not None:
                    if Q1 - 1.5 * IQR <= point <= Q3 + 1.5 * IQR:
                        info.append(point)
                    else:
                        info.append(None)
                else:
                    info.append(None)

            return info

        pages = [
            instance for instance in self.item_instances.values() 
            if page1 <= instance.id <= page2
        ]

        timestamps = [
            instance.time_scanned for instance in pages
            if page1 <= instance.id <= page2
        ]
        volumes = [
            None if instance.volume == 0 else instance.volume 
            for instance in pages 
            if page1 <= instance.id <= page2
        ]

        lowest_sells = [
            None if instance.average_sell == 0 else instance.average_sell
            for instance in pages 
            if page1 <= instance.id <= page2
        ]
        highest_buys = [
            None if instance.average_buy == 0 else instance.average_buy
            for instance in pages
            if page1 <= instance.id <= page2
        ]

        if iqr:
            volumes = interQuartileRange(volumes)
            lowest_sells = interQuartileRange(lowest_sells)
            highest_buys = interQuartileRange(highest_buys)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=timestamps, y=volumes, name='Volume', yaxis='y2', mode='lines', fill='tozeroy'))
        fig.add_trace(go.Scatter(x=timestamps, y=lowest_sells, mode='lines', name='Average Sell'))
        fig.add_trace(go.Scatter(x=timestamps, y=highest_buys, mode='lines', name='Average Buy'))
        fig.update_layout(
            title=f"Market Changes for {self.name}",
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(
                title='Price',
                side='left'
            ),
            yaxis2=dict(
                title='Volume',
                overlaying='y',
                side='right'
            ),
            barmode="overlay",
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            ),
            width=1200,
        )

        fig_bytes = pio.to_image(fig, format='png')
        return discord.File(fp=BytesIO(fig_bytes), filename="graph.png")

class MarketChangeState(Enum):
    LISTINGS = 0
    CHANGES = 1

class MarketChangeView(discord.ui.View):

    def __init__(self, market_change_instance: MarketHistoryInstance):
        super().__init__(timeout=300)
        self.market_change_instance = market_change_instance
        self.current_page = market_change_instance.max_page

        self.state = MarketChangeState.LISTINGS

    def __update_buttons(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label == "Listings":
                    child.disabled = self.state == MarketChangeState.LISTINGS
                elif child.label == "Changes":
                    child.disabled = self.state == MarketChangeState.CHANGES
                elif child.label == "Previous":
                    child.disabled = self.current_page == self.market_change_instance.min_page
                elif child.label == "Next":
                    child.disabled = self.current_page == self.market_change_instance.max_page


    @discord.ui.button(label="Listings", style=discord.ButtonStyle.primary, row=1, disabled=True)
    async def listings(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.state = MarketChangeState.LISTINGS
        self.__update_buttons()
        await interaction.response.edit_message(view=self, embed=self.market_change_instance[self.current_page].embed.set_image(url="attachment://graph.png"))

    @discord.ui.button(label="Changes", style=discord.ButtonStyle.primary, row=1)
    async def changes(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.state = MarketChangeState.CHANGES
        self.__update_buttons()
        await interaction.response.edit_message(view=self, embed=(await self.market_change_instance.changes_for(self.current_page)).set_image(url="attachment://graph.png"))

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, row=2)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.__update_buttons()

        if self.state == MarketChangeState.LISTINGS:
            await interaction.response.edit_message(view=self, embed=self.market_change_instance[self.current_page].embed.set_image(url="attachment://graph.png"))
        else:
            await interaction.response.edit_message(view=self, embed=(await self.market_change_instance.changes_for(self.current_page)).set_image(url="attachment://graph.png"))

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, row=2, disabled=True)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.__update_buttons()

        if self.state == MarketChangeState.LISTINGS:
            await interaction.response.edit_message(view=self, embed=self.market_change_instance[self.current_page].embed.set_image(url="attachment://graph.png"))
        else:
            await interaction.response.edit_message(view=self, embed=(await self.market_change_instance.changes_for(self.current_page)).set_image(url="attachment://graph.png"))