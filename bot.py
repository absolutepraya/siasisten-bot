import discord
import os
import json
from discord.ext import commands, tasks
from dotenv import load_dotenv
from scraper_requests import ScraperRequests
import datetime as d
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment Variables
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
CHANNEL = int(os.getenv("DISCORD_CHANNEL"))
NLINE = "\n"
FMT = "%Y-%m-%d %H:%M:%S.%f"

# Discord Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # If enabled in Developer Portal

# Initialize Bot
bot = commands.Bot(command_prefix="-", intents=intents)

# Initialize Scraper
try:
    scraper = ScraperRequests()
except Exception as e:
    logger.exception(
        "Failed to initialize the scraper. The bot will run without scraping functionality."
    )
    scraper = None

# Data Storage
data = tuple()
if os.path.exists("data.json"):
    with open("data.json", "r") as f:
        temp = json.load(f)
        try:
            data = (d.datetime.strptime(temp["time"], FMT), temp["data"])
            logger.info("Loaded existing data from data.json.")
        except Exception as e:
            logger.exception(f"Error parsing data.json: {e}")
            data = tuple()


def write_json(data):
    with open("data.json", "w") as f:
        json.dump({"time": data[0].strftime(FMT), "data": data[1]}, f, indent=4)
    logger.info("Updated data.json with new data.")


@bot.event
async def on_ready():
    global data
    logger.info(f"{bot.user} has connected to Discord!")
    for guild in bot.guilds:
        if guild.name == GUILD:
            break
    else:
        logger.error(
            f"Guild '{GUILD}' not found. Please check the DISCORD_GUILD environment variable."
        )
        return
    logger.info(
        f"{bot.user} is connected to the following guild:\n"
        f"{guild.name} (id: {guild.id})"
    )
    if scraper:
        update_list_lowongan_1hr.start()
    else:
        logger.error("Scraper is not initialized. Background task will not start.")


@bot.command(name="display")
async def display_list_lowongan(context):
    global data
    if not data:
        response = discord.Embed(
            title="There's no lowongan data.",
            description="Update the data using command `-update`.",
        )
    else:
        now = data[0]
        list_lowongan = data[1]
        description = "List lowongan asdos yang buka:\n\n" + "\n\n".join(
            [
                f"• **{entry['title']}**\n[Daftar]({entry['daftar_link']})"
                for entry in list_lowongan
            ]
        )
        response = discord.Embed(
            title=f"Info Loker (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
            description=description,
        )
    await context.send(embed=response)


@bot.command(name="update")
async def update_list_lowongan(context):
    global data
    if not scraper:
        await context.send("Scraper is not initialized. Unable to update lowongan.")
        return

    new_data = scraper.get_lowongan()
    now = d.datetime.now()

    if not new_data:
        await context.send("Failed to retrieve lowongan data.")
        return

    if not data or set([entry["title"] for entry in new_data]) != set(
        [entry["title"] for entry in data[1]]
    ):
        if data:
            existing_titles = set([entry["title"] for entry in data[1]])
            new_entries = [
                entry for entry in new_data if entry["title"] not in existing_titles
            ]
        else:
            new_entries = new_data

        if new_entries:
            description = "\n\n".join(
                [
                    f"• **{entry['title']}**\n[Daftar]({entry['daftar_link']})"
                    for entry in new_entries
                ]
            )
            response = discord.Embed(
                title=f"Lowongan baru unlocked! (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
                description=description,
            )
        else:
            response = discord.Embed(
                title=f"Update (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
                description="Belum ada lowongan baru.",
            )
    else:
        response = discord.Embed(
            title=f"Update (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
            description="Belum ada lowongan baru.",
        )
    data = (now, new_data)
    write_json(data)
    await context.send(embed=response)


@bot.command(name="h")
async def get_help(context):
    response = discord.Embed(
        title="Bot Usage",
        description=(
            "Prefix: `-`\n\n"
            "Available commands:\n"
            "**h** : Lists all available commands\n"
            "**display** : Displays the current lowongan list (might be outdated)\n"
            "**update** : Updates the lowongan list, displays the difference\n"
            "**clear** : Clears stored lowongan data\n"
        ),
    )
    await context.send(embed=response)


@bot.command(name="clear")
async def clear_data(context):
    global data
    data = tuple()
    if os.path.exists("data.json"):
        os.remove("data.json")
        logger.info("Cleared data.json.")
    response = discord.Embed(title="Data cleared!")
    await context.send(embed=response)


@tasks.loop(minutes=30)
async def update_list_lowongan_1hr():
    global data
    if not scraper:
        logger.error("Scraper is not initialized. Cannot perform scheduled update.")
        return

    new_data = scraper.get_lowongan()
    now = d.datetime.now()

    if not new_data:
        logger.warning("Failed to retrieve lowongan data during scheduled update.")
        return

    if not data:
        description = "\n\n".join(
            [
                f"• **{entry['title']}**\n[Daftar]({entry['daftar_link']})"
                for entry in new_data
            ]
        )
        response = discord.Embed(
            title=f"Info Loker (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
            description=description,
        )
    else:
        existing_titles = set([entry["title"] for entry in data[1]])
        new_entries = [
            entry for entry in new_data if entry["title"] not in existing_titles
        ]

        if new_entries:
            description = "\n\n".join(
                [
                    f"• **{entry['title']}**\n[Daftar]({entry['daftar_link']})"
                    for entry in new_entries
                ]
            )
            response = discord.Embed(
                title=f"Lowongan baru unlocked! (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
                description=description,
            )
        else:
            response = discord.Embed(
                title=f"Update (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
                description="Belum ada lowongan baru.",
            )

    data = (now, new_data)
    write_json(data)
    channel = bot.get_channel(CHANNEL)
    if channel:
        await channel.send(embed=response)
        logger.info("Scheduled lowongan update sent successfully.")
    else:
        logger.error(f"Channel with ID {CHANNEL} not found.")


@update_list_lowongan_1hr.before_loop
async def before_update_lowongan_1hr():
    await bot.wait_until_ready()


bot.run(TOKEN)
