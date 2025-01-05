import discord
from discord import app_commands
from keep_alive import keep_alive
from discord.ext import commands, tasks
import os
import datetime
import json
from replit import db

keep_alive()

# Intents for the bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# Token from environment variable
bot_token = os.environ['bot_token']

tree = bot.tree

# Storage for warnings and offers
warns = {}
offers = {}
next_offer_id = 1
free_ids = set()

# Channel IDs for data persistence
warn_channel_id = 1277658786785660940
offers_channel_id = 1303704862877290628
time_channel_id = 1323237153127530547


# Load warning data from channel
async def load_warns():
    global warns
    channel = bot.get_channel(warn_channel_id)
    if channel:
        async for message in channel.history(limit=1):
            try:
                warns = json.loads(message.content)
                print("Warning data successfully loaded.")
            except json.JSONDecodeError:
                print("Failed to load warning data. Invalid JSON format.")
                warns = {}


# Save warning data to channel
async def save_warns():
    channel = bot.get_channel(warn_channel_id)
    if channel:
        await channel.purge(limit=10)
        await channel.send(json.dumps(warns))
        print("Warning data successfully saved.")


# Load offers from Replit database
async def load_offers():
    global offers, next_offer_id, free_ids
    offers = db.get("offers", {})
    next_offer_id = db.get("next_offer_id", 1)
    free_ids = set(db.get("free_ids", []))
    print("Offer data successfully loaded from Replit database.")


# Save offers to Replit database
async def save_offers():
    db["offers"] = offers
    db["next_offer_id"] = next_offer_id
    db["free_ids"] = list(free_ids)
    print("Offer data successfully saved to Replit database.")


# Create a new offer
@tree.command(name="create_offer", description="Create a new offer")
async def create_offer(interaction: discord.Interaction, item_name: str, total_price: float, amount: int, la_spawn: str, x: int, y: int, z: int):
    global next_offer_id, free_ids

    seller = interaction.user.name
    if seller not in offers:
        offers[seller] = []

    piece_price = total_price / amount
    offer_id = free_ids.pop() if free_ids else next_offer_id
    if offer_id == next_offer_id:
        next_offer_id += 1

    offer = {
        "id": offer_id,
        "item_name": item_name,
        "total_price": total_price,
        "amount": amount,
        "piece_price": piece_price,
        "seller": seller,
        "la_spawn": la_spawn,
        "coordinates": {"x": x, "y": y, "z": z}
    }

    offers[seller].append(offer)
    await save_offers()
    await interaction.response.send_message(
        f"Offer for {item_name} created successfully! ID: {offer_id}",
        ephemeral=True)


# Delete an offer
@tree.command(name="delete_offer", description="Delete an existing offer")
async def delete_offer(interaction: discord.Interaction, offer_id: int):
    global offers, free_ids

    offer_to_delete = None
    for seller, seller_offers in offers.items():
        for offer in seller_offers:
            if offer['id'] == offer_id:
                offer_to_delete = offer
                break
        if offer_to_delete:
            break

    if not offer_to_delete:
        await interaction.response.send_message(
            f"No offer found with ID {offer_id}.", ephemeral=True)
        return

    if interaction.user.name != offer_to_delete['seller'] and not discord.utils.get(interaction.user.roles, name="Server Staff"):
        await interaction.response.send_message(
            "You are not authorized to delete this offer.", ephemeral=True)
        return

    offers[offer_to_delete['seller']].remove(offer_to_delete)
    free_ids.add(offer_id)
    await save_offers()
    await interaction.response.send_message(
        f"Offer with ID {offer_id} deleted successfully.", ephemeral=True)

COLUMN_WIDTH_ID = 8
COLUMN_WIDTH_ITEM = 20
COLUMN_WIDTH_SELLER = 20
COLUMN_WIDTH_LOCATION = 20
COLUMN_WIDTH_COORDS = 15

# View all offers
@tree.command(name="all_offers", description="View all offers")
@app_commands.checks.has_role("Server Staff")
async def all_offers(interaction: discord.Interaction):
    if not offers:
        await interaction.response.send_message("No offers available.", ephemeral=True)
        return

    offer_messages = []
    for seller, seller_offers in offers.items():
        for offer in seller_offers:
            total_price = int(offer['total_price']) if offer['total_price'].is_integer() else offer['total_price']
            piece_price = int(offer['piece_price']) if offer['piece_price'].is_integer() else offer['piece_price']
            offer_messages.append(
                f"{str(offer['id']).ljust(COLUMN_WIDTH_ID)} "
                f"**{offer['item_name'].ljust(COLUMN_WIDTH_ITEM)}** "
                f"<:real_price:1318277420918374410> {total_price} / 64     "
                f"<:single_price:1318277414924587028> {piece_price} / 1      "
                f"<:seller:1318277419471343659> {offer['seller'].ljust(COLUMN_WIDTH_SELLER)} "
                f"<:la_spawn:1318277413389467738> {offer['la_spawn'].ljust(COLUMN_WIDTH_LOCATION)} "
                f"<:cords:1318277416380268645> {offer['coordinates']['x']} {offer['coordinates']['y']} {offer['coordinates']['z']}".ljust(COLUMN_WIDTH_COORDS)
            )

    await interaction.response.send_message("\n".join(offer_messages), ephemeral=True)



# View own offers
@tree.command(name="my_offers", description="View your own offers")
async def my_offers(interaction: discord.Interaction):
    seller = interaction.user.name
    if seller not in offers or not offers[seller]:
        await interaction.response.send_message("You don't have any offers.", ephemeral=True)
        return

    offer_messages = []
    for offer in offers[seller]:
        total_price = int(offer['total_price']) if offer['total_price'].is_integer() else offer['total_price']
        piece_price = int(offer['piece_price']) if offer['piece_price'].is_integer() else offer['piece_price']
        offer_messages.append(
            f"{str(offer['id']).ljust(COLUMN_WIDTH_ID)} "
            f"**{offer['item_name'].ljust(COLUMN_WIDTH_ITEM)}** "
            f"<:real_price:1318277420918374410> {total_price} / 64     "
            f"<:single_price:1318277414924587028> {piece_price} / 1     "
            f"<:seller:1318277419471343659> {offer['seller'].ljust(COLUMN_WIDTH_SELLER)} "
            f"<:la_spawn:1318277413389467738> {offer['la_spawn'].ljust(COLUMN_WIDTH_LOCATION)} "
            f"<:cords:1318277416380268645> {offer['coordinates']['x']} {offer['coordinates']['y']} {offer['coordinates']['z']}".ljust(COLUMN_WIDTH_COORDS)
        )

    await interaction.response.send_message("\n".join(offer_messages), ephemeral=True)

# Search for offers
@tree.command(name="search_offers", description="Search offers")
async def search_offers(interaction: discord.Interaction, item_name: str = None, max_price_per1: float = None, seller: str = None, location: str = None):
    results = []

    for seller_name, seller_offers in offers.items():
        for offer in seller_offers:
            if item_name and item_name.lower() not in offer['item_name'].lower():
                continue
            if max_price_per1 and offer['piece_price'] > max_price_per1:
                continue
            if seller and seller.lower() != seller_name.lower():
                continue
            if location and location.lower() not in offer['la_spawn'].lower():
                continue

            results.append(offer)

    results.sort(key=lambda o: o["piece_price"])
    if results:
        header = f"**Offers for: {item_name}**\n" if item_name else "**Matching Offers:**\n"
        formatted_results = [
            f"{str(offer['id']).ljust(COLUMN_WIDTH_ID)} "
            f"<:real_price:1318277420918374410> {int(offer['total_price']) if offer['total_price'].is_integer() else offer['total_price']} / 64     "
            f"<:single_price:1318277414924587028> {int(offer['piece_price']) if offer['piece_price'].is_integer() else offer['piece_price']} / 1     "
            f"<:seller:1318277419471343659> {offer['seller'].ljust(COLUMN_WIDTH_SELLER)} "
            f"<:la_spawn:1318277413389467738> {offer['la_spawn'].ljust(COLUMN_WIDTH_LOCATION)} "
            f"<:cords:1318277416380268645> {offer['coordinates']['x']} {offer['coordinates']['y']} {offer['coordinates']['z']}".ljust(COLUMN_WIDTH_COORDS)
            for offer in results
        ]
        await interaction.response.send_message(header + "\n".join(formatted_results), ephemeral=True)
    else:
        await interaction.response.send_message("No matching offers found.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await load_offers()
    try:
        await tree.sync()
        print("Slash commands synced globally.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Run the bot
bot.run(bot_token)
