import discord
import os
import json
import datetime as d
import logging
from discord.ext import commands, tasks
from dotenv import load_dotenv
from scraper_requests import ScraperRequests
from zoneinfo import ZoneInfo

# Timezone
JAKARTA_TZ = ZoneInfo("Asia/Jakarta")


def get_suffix(day: int) -> str:
    """
    Returns the ordinal suffix for a given day.
    """
    if 11 <= day <= 13:
        return "th"
    elif day % 10 == 1:
        return "st"
    elif day % 10 == 2:
        return "nd"
    elif day % 10 == 3:
        return "rd"
    else:
        return "th"


def get_formatted_time() -> str:
    """
    Returns the current time formatted with timezone and ordinal suffix.
    """
    now = d.datetime.now(JAKARTA_TZ)
    suffix = get_suffix(now.day)
    return now.strftime(f"%b {now.day}{suffix}, %Y — %H:%M")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment Variables
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD"))
CHANNEL = int(os.getenv("DISCORD_CHANNEL"))
NLINE = "\n"
FMT = "%Y-%m-%d %H:%M:%S.%f"

# Discord Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

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
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        logger.error(
            f"Guild with ID '{GUILD_ID}' not found. Please check the DISCORD_GUILD_ID environment variable."
        )
        return
    logger.info(
        f"{bot.user} is connected to the following guild:\n"
        f"{guild.name} (ID: {guild.id})"
    )
    if scraper:
        logger.info("Starting background task update_list_lowongan_5mins.")
        update_list_lowongan_5mins.start()
    else:
        logger.error("Scraper is not initialized. Background task will not start.")


@bot.command(name="display", aliases=["d"])
async def display_list_lowongan(context):
    global data
    if not data:
        response = discord.Embed(
            title="There's no vacancy data.",
            description="Update the data using command `-update`.",
        )
    else:
        list_lowongan = data[1]
        description = "List of open TA vacancies:\n\n" + "\n\n".join(
            [
                f"• **{entry['title']}**\n{entry['jumlah_pelamar_diterima']}/{entry['jumlah_lowongan']} slots filled - {entry['jumlah_pelamar']} applicants\n[Daftar]({entry['daftar_link']})"
                for entry in list_lowongan
            ]
        )
        response = discord.Embed(
            title=f"TA Vacancy Info (as of {get_formatted_time()})",
            description=description,
        )
    await context.send(embed=response)


@bot.command(name="update", aliases=["u"])
async def update_list_lowongan(context):
    global data
    if not scraper:
        await context.send("Scraper is not initialized. Unable to update vacancy.")
        return

    new_data = scraper.get_lowongan()
    now = d.datetime.now()

    if not new_data:
        await context.send("Failed to retrieve vacancy data.")
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
                title=f"New vacancies found! (as of {get_formatted_time()})",
                description=description,
            )
        else:
            response = discord.Embed(
                title=f"Update (as of {get_formatted_time()})",
                description="No new vacancies found.",
            )
    else:
        response = discord.Embed(
            title=f"Update (as of {get_formatted_time()})",
            description="No new vacancies found.",
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
            "• `-display` or `-d`: Display the list of TA vacancies.\n"
            "• `-update` or `-u`: Update the list of TA vacancies.\n"
            "• `-clear` or `-c`: Clear the data stored in the bot.\n"
            "• `-h`: Display this help message."
        ),
    )
    await context.send(embed=response)


@bot.command(name="clear", aliases=["c"])
async def clear_data(context):
    global data
    data = tuple()
    if os.path.exists("data.json"):
        os.remove("data.json")
        logger.info("Cleared data.json.")
    response = discord.Embed(title="Data cleared!")
    await context.send(embed=response)


@tasks.loop(minutes=5)
async def update_list_lowongan_5mins():
    # Logger
    logger.info("--- Performing 5-mins interval scheduled update...")

    channel = bot.get_channel(CHANNEL)
    if not channel:
        logger.error(f"--- Channel with ID {CHANNEL} not found.")
        return

    global data
    if not scraper:
        logger.error("--- Scraper is not initialized. Cannot perform scheduled update.")
        return

    new_data = scraper.get_lowongan()
    now = d.datetime.now()

    if not new_data:
        logger.warning("--- Failed to retrieve vacancy data during scheduled update.")
        return

    if not data:
        description = "\n\n".join(
            [
                f"• **{entry['title']}**\n[Daftar]({entry['daftar_link']})"
                for entry in new_data
            ]
        )
        response = discord.Embed(
            title=f"TA Vacancy Info (as of {get_formatted_time()})",
            description=description,
        )
        await channel.send(embed=response)

        # Logger
        logger.info("Initial data update completed.")
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
                title=f"List of open TA vacancies (as of {get_formatted_time()})",
                description=description,
            )
            await channel.send(embed=response)

            # Logger
            logger.info(f"New vacancies found during scheduled update: {new_entries}")
        else:
            # Logger
            logger.info("No new vacancies found during scheduled update.")

    data = (now, new_data)
    write_json(data)

    # Logger
    logger.info("--- Interval scheduled update completed.")


@update_list_lowongan_5mins.before_loop
async def before_update_lowongan_5mins():
    await bot.wait_until_ready()


bot.run(TOKEN)
