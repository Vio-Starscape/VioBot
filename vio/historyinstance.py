import discord
import plotly.graph_objects as go
import plotly.io as pio
import plotly.subplots as splt
import numpy as np
from io import BytesIO
from enum import Enum
from typing import Dict, Optional
from scipy.signal import savgol_filter

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
    
    def __iter__(self):
        return iter(sorted(self.item_instances.values(), key=lambda x: x.time_scanned))
    
    def __len__(self):
        return len(self.item_instances)
    
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
    
    def latest_usable(self) -> ItemInstance:
        for i in range(self.max_page, self.min_page, -1):
            if self.item_instances[i].valid:
                return self.item_instances[i]
        return self.item_instances[self.max_page]
    
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
        return await self.graph_between_pages()
    
    def __interpolate_zeros(self, lst) -> list:
        # Kevin Method the Entire Thing
        average = float(np.average([i for i in lst if i != 0]))
        lst = [i if i < average * 2 else 0 for i in lst]

        # Find the last non-zero value in the list
        last_non_zero = next((x for x in reversed(lst) if x != 0), average)

        i = 0
        while i < len(lst):
            if lst[i] == 0:
                # Find the next non-zero number and the number of zeros
                next_non_zero_index = i + 1
                while next_non_zero_index < len(lst) and lst[next_non_zero_index] == 0:
                    next_non_zero_index += 1

                # If there's no non-zero number after the zeros, break the loop
                if next_non_zero_index == len(lst):
                    break

                # Calculate the step size
                prev_non_zero = lst[i - 1] if i > 0 else 0
                next_non_zero = lst[next_non_zero_index]
                num_zeros = next_non_zero_index - i
                step_size = (next_non_zero - prev_non_zero) / (num_zeros + 1)

                # Replace the zeros
                for j in range(i, next_non_zero_index):
                    lst[j] = round(prev_non_zero + step_size * (j - i + 1), 2)

                # Move the index
                i = next_non_zero_index
            else:
                i += 1

        # Replace trailing zeros with the last non-zero value
        for i in reversed(range(len(lst))):
            if lst[i] == 0:
                lst[i] = last_non_zero
            else:
                break  # Stop as soon as we find a non-zero value

        return lst
    

    async def graph_between_pages(self, *, page1: Optional[int] = None, page2: Optional[int] = None) -> discord.File:
        """Graph the difference between two pages."""
        if page1 is None:
            page1 = self.min_page
        if page2 is None:
            page2 = self.max_page

        if page1 > page2:
            page1, page2 = page2, page1
        if page1 < self.min_page:
            page1 = self.min_page
        if page2 > self.max_page:
            page2 = self.max_page

        times = [i.time_scanned for i in self.item_instances.values() if page1 <= i.id <= page2]
        average_sell = self.__interpolate_zeros([i.average_sell() for i in self.item_instances.values() if page1 <= i.id <= page2])
        average_buy = self.__interpolate_zeros([i.average_buy() for i in self.item_instances.values() if page1 <= i.id <= page2])
        volume_buy = self.__interpolate_zeros([i.buy_volume for i in self.item_instances.values() if page1 <= i.id <= page2])
        volume_sell = self.__interpolate_zeros([i.sell_volume for i in self.item_instances.values() if page1 <= i.id <= page2])

        average_sell_smooth = savgol_filter(average_sell, 51, 3)  # window size 51, polynomial order 3
        average_buy_smooth = savgol_filter(average_buy, 51, 3)
        volume_buy_smooth = savgol_filter(volume_buy, 51, 3)
        volume_sell_smooth = savgol_filter(volume_sell, 51, 3)

        fig = splt.make_subplots(
            rows=2, 
            cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.1, 
            subplot_titles=("Sell", "Buy"),
            specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
            )
        
        # Sell
        fig.add_trace(
            go.Scatter(x=times, y=average_sell_smooth, mode="lines", name="Average Sell Price", line=dict(color='#003300')),
            row=1,
            col=1,
            secondary_y=True
        )
        fig.add_trace(
            go.Scatter(x=times, y=volume_sell_smooth, name="Volume", fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.5)', line=dict(color='#00ff00')),
            row=1,
            col=1
        )

        # Buy
        fig.add_trace(
            go.Scatter(x=times, y=average_buy_smooth, mode="lines", name="Average Buy Price", line=dict(color='#330000')),
            row=2,
            col=1,
            secondary_y=True
        )
        fig.add_trace(
            go.Scatter(x=times, y=volume_buy_smooth, name="Volume", fill='tozeroy', line=dict(color='#ff0000'), fillcolor='rgba(255, 0, 0, 0.5)'
                    ),
            row=2,
            col=1,
        )

        # fig.update_traces(mode="lines", selector=dict(type='scatter')) 
        fig.update_traces(mode="lines")

        fig.update_layout(
                title=f"Market Changes for {self.name}",
                font=dict(
                    family="Inconsolata, monospace",
                    size=15,
                    color="White"
                ),
                paper_bgcolor='gray',
                plot_bgcolor='gray',
                yaxis=dict(
                    showgrid=False,
                    title='Volume',
                    side='left',
                    # domain=[0.5, 1]
                ),
                yaxis2=dict(
                    showgrid=False,
                    title='Price',
                    overlaying='y',
                    side='right',
                    tickmode="array",
                    # domain=[0.5, 1]
                ),
                yaxis3=dict(
                    showgrid=False,
                    title='Volume',
                    side='left',
                    # domain=[0.5, 1]
                ),
                yaxis4=dict(
                    showgrid=False,
                    title='Price',
                    overlaying='y3',
                    side='right',
                    tickmode="array",
                    # domain=[0.5, 1]
                ),
                barmode="overlay",
                legend=dict(
                    yanchor="top",
                    y=1.08,
                    xanchor="left",
                    x=0.3,
                    bgcolor="rgba(0,0,0,0)",
                    orientation="h"
                ),
                width=1500,
                height=700,
                shapes=[
                    dict(
                        type="rect",
                        xref="paper",
                        yref="paper",
                        x0=0,
                        y0=0.55,
                        x1=0.94,
                        y1=1,
                        line=dict(
                            color="Black",
                            width=2,
                        ),
                    ),
                    dict(
                        type="rect",
                        xref="paper",
                        yref="paper",
                        x0=0,
                        y0=0,
                        x1=0.94,
                        y1=0.45,
                        line=dict(
                            color="Black",
                            width=2,
                        ),
                    )
                ],
                margin=dict(  # Add this dictionary
                    l=85,  # left margin
                    r=0,  # right margin
                    b=50,  # bottom margin
                    t=50,  # top margin
                    pad=10,  # padding,
                )
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