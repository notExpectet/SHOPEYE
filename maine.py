import discord
from discord import app_commands
from discord.ext import commands
import os
import json

# Intents for the bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# Token from environment variable
bot_token = os.environ.get('bot_token')

# Slash command tree
tree = bot.tree

# Storage for warnings and offers
warns_file = "warns.json"
offers_file = "offers.json"

warns = {}
offers = {}
next_offer_id = 1
free_ids = set()

# Load data from files
def load_data():
    global warns, offers, next_offer_id, free_ids
    try:
        with open(warns_file, "r") as f:
            warns = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        warns = {}

    try:
        with open(offers_file, "r") as f:
            data = json.load(f)
            offers = data.get("offers", {})
            next_offer_id = data.get("next_offer_id", 1)
            free_ids = set(data.get("free_ids", []))
    except (FileNotFoundError, json.JSONDecodeError):
        offers = {}
        next_offer_id = 1
        free_ids = set()

# Save data to files
def save_data():
    with open(warns_file, "w") as f:
        json.dump(warns, f, indent=4)

    with open(offers_file, "w") as f:
        json.dump({
            "offers": offers,
            "next_offer_id": next_offer_id,
            "free_ids": list(free_ids)
        }, f, indent=4)

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
    save_data()
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
    save_data()
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
                f"<:cords:1318277416380268645> {offer['coordinates']['x']} {offer['coordinates']['y']} {offer['coordinates']['z']}"
            )

    await interaction.response.send_message("\n".join(offer_messages), ephemeral=True)

# Run the bot
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    load_data()
    try:
        await tree.sync()
        print("Slash commands synced globally.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

bot.run(bot_token)
