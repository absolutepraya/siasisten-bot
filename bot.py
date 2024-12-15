import discord
import os
import json
import datetime as dt
import logging
from discord.ext import commands, tasks
from dotenv import load_dotenv
from scraper_requests import ScraperRequests
from zoneinfo import ZoneInfo
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Environment Variables
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD"))
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL"))
NLINE = "\n"
FMT = "%Y-%m-%d %H:%M:%S.%f%z"

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
    now = dt.datetime.now(JAKARTA_TZ)
    suffix = get_suffix(now.day)
    return now.strftime(f"%b {now.day}{suffix}, %Y — %H:%M")


class VacancyBot(commands.Cog):
    """
    A Cog for handling vacancy-related commands and background tasks.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scraper = None
        self.data = ()
        self.load_data()
        self.initialize_scraper()

    def load_data(self):
        """
        Loads vacancy data from a JSON file.
        """
        if os.path.exists("data.json"):
            try:
                with open("data.json", "r") as f:
                    temp = json.load(f)
                time_str = temp["time"]
                parsed_time = dt.datetime.strptime(time_str, FMT).astimezone(JAKARTA_TZ)
                self.data = (parsed_time, temp["data"])
                logger.info("Loaded existing data from data.json.")
            except Exception as e:
                logger.exception(f"Error parsing data.json: {e}")
                self.data = ()
        else:
            logger.info("No existing data.json found. Starting fresh.")
            self.data = ()

    def write_json(self, data: tuple):
        """
        Writes vacancy data to a JSON file.
        """
        try:
            with open("data.json", "w") as f:
                time_str = data[0].strftime(FMT)
                json.dump({"time": time_str, "data": data[1]}, f, indent=4)
            logger.info("Updated data.json with new data.")
        except Exception as e:
            logger.exception(f"Failed to write data.json: {e}")

    def initialize_scraper(self):
        """
        Initializes the scraper.
        """
        try:
            self.scraper = ScraperRequests()
            logger.info("Scraper initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize the scraper!")
            self.scraper = None

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event handler for when the bot is ready.
        """
        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            logger.info(
                f"{self.bot.user} is connected to the following guild:\n{guild.name} (id: {guild.id})"
            )
        else:
            logger.error(
                f"Guild with ID '{GUILD_ID}' not found. Please check the DISCORD_GUILD_ID environment variable."
            )
            return

        if self.scraper:
            logger.info("Starting background task for vacancy updates.")
            self.vacancies_update_5mins.start()
        else:
            logger.error("Scraper is not initialized. Background task will not start.")

    @commands.command(name="display", aliases=["d"])
    async def display_list_lowongan(self, ctx: commands.Context):
        """
        Displays the current list of vacancies.
        """
        formatted_time = get_formatted_time()
        if not self.data:
            response = discord.Embed(
                title="There's no vacancies data.",
                description="Update the data using command `-update`.",
            )
        else:
            list_lowongan = self.data[1]
            description = "List of open TA vacancies:\n\n" + "\n\n".join(
                [
                    f"• **{entry['title']}**\n[Daftar]({entry['daftar_link']})"
                    for entry in list_lowongan
                ]
            )
            response = discord.Embed(
                title=f"TA Vacancies (as of {formatted_time})",
                description=description,
            )
        await ctx.send(embed=response)

    @commands.command(name="update", aliases=["u"])
    async def update_list_lowongan(self, ctx: commands.Context):
        """
        Manually updates the list of vacancies.
        """
        formatted_time = get_formatted_time()
        if not self.scraper:
            await ctx.send("Scraper is not initialized. Unable to update vacancies.")
            return

        new_data = self.scraper.get_lowongan()
        now = dt.datetime.now(JAKARTA_TZ)

        if not new_data:
            await ctx.send("Failed to retrieve vacancy data.")
            return

        if not self.data or set(entry["title"] for entry in new_data) != set(
            entry["title"] for entry in self.data[1]
        ):
            if self.data:
                existing_titles = set(entry["title"] for entry in self.data[1])
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
                    title=f"New vacancies found! (as of {formatted_time})",
                    description=description,
                )
            else:
                response = discord.Embed(
                    title=f"Update (as of {formatted_time})",
                    description="No new vacancies found.",
                )
        else:
            response = discord.Embed(
                title=f"Update (as of {formatted_time})",
                description="No new vacancies found.",
            )
        self.data = (now, new_data)
        self.write_json(self.data)
        await ctx.send(embed=response)

    @commands.command(name="help", aliases=["h"])
    async def get_help(self, ctx: commands.Context):
        """
        Displays help information.
        """
        response = discord.Embed(
            title="Bot Usage",
            description=(
                "Prefix: `-`\n\n"
                "Available commands:\n"
                "• `-display` or `-d`: Display the list of TA vacancies.\n"
                "• `-update` or `-u`: Update the list of TA vacancies.\n"
                "• `-clear` or `-c`: Clear the data stored in the bot.\n"
                "• `-help` or `-h`: Display this help message."
            ),
        )
        await ctx.send(embed=response)

    @commands.command(name="clear", aliases=["c"])
    async def clear_data(self, ctx: commands.Context):
        """
        Clears the stored vacancy data.
        """
        self.data = ()
        try:
            if os.path.exists("data.json"):
                os.remove("data.json")
                logger.info("Cleared data.json.")
        except Exception as e:
            logger.exception(f"Failed to clear data.json: {e}")
        response = discord.Embed(title="Data cleared!")
        await ctx.send(embed=response)

    async def send_vacancy_update(
        self, new_entries: List[Dict[str, str]], formatted_time: str
    ):
        """
        Sends a formatted embed message to the designated channel with new vacancies.
        """
        if not new_entries:
            response = discord.Embed(
                title=f"Update (as of {formatted_time})",
                description="No new vacancies found.",
            )
        else:
            description = "\n\n".join(
                [
                    f"• **{entry['title']}**\n[Daftar]({entry['daftar_link']})"
                    for entry in new_entries
                ]
            )
            response = discord.Embed(
                title=f"New vacancies found! (as of {formatted_time})",
                description=description,
            )
        channel = self.bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(embed=response)
            logger.info("Sent vacancy update successfully.")
        else:
            logger.error(f"Channel with ID {CHANNEL_ID} not found.")

    async def perform_update(self):
        """
        Performs the update logic used by both the command and the background task.
        """
        if not self.scraper:
            logger.error("Scraper is not initialized. Cannot perform update.")
            return

        new_data = self.scraper.get_lowongan()
        now = dt.datetime.now(JAKARTA_TZ)
        formatted_time = get_formatted_time()

        if not new_data:
            logger.warning("Failed to retrieve vacancy data.")
            return

        if not self.data:
            new_entries = new_data
        else:
            existing_titles = set(entry["title"] for entry in self.data[1])
            new_entries = [
                entry for entry in new_data if entry["title"] not in existing_titles
            ]

        if new_entries:
            self.data = (now, new_data)
            self.write_json(self.data)
            await self.send_vacancy_update(new_entries, formatted_time)
        else:
            logger.info("No new vacancies found during update.")

        logger.info("Update task completed.")

    @tasks.loop(minutes=5)
    async def vacancies_update_5mins(self):
        """
        Background task that checks for new vacancies every 30 minutes.
        """
        try:
            logger.info("Running scheduled vacancy update task.")
            await self.perform_update()
        except Exception as e:
            logger.exception(f"An error occurred during scheduled update: {e}")

    @vacancies_update_5mins.before_loop
    async def before_vacancies_update_5mins(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        """
        Handles errors for commands.
        """
        logger.error(f"Error in command '{ctx.command}': {error}")
        await ctx.send("An error occurred while processing the command.")


# Initialize the bot and add the Cog
bot = commands.Bot(command_prefix="-", intents=intents)

bot.add_cog(VacancyBot(bot))

# Run the bot
bot.run(TOKEN)
