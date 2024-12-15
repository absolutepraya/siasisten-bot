import discord
import os
import json
from discord.ext import commands, tasks
from dotenv import load_dotenv
from scraper_requests import ScraperRequests
import datetime as d

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL = int(os.getenv('DISCORD_CHANNEL'))
NLINE = "\n"
FMT = '%Y-%m-%d %H:%M:%S.%f'

intents = discord.Intents.default()
intents.message_content = True
data = tuple()
if os.path.exists('data.json'):
    with open('data.json', 'r') as f:
        temp = json.load(f)
        data = (d.datetime.strptime(temp['time'], FMT), temp['data'])

bot = commands.Bot(command_prefix="-", intents=intents)
scraper = ScraperRequests()


def write_json(data):
    with open("data.json", "w") as f:
        f.write(json.dumps({"time": str(data[0]), "data": data[1]}, indent=4))


@bot.event
async def on_ready():
    global data
    print(f"{bot.user} has connected to Discord!")
    for guild in bot.guilds:
        if guild.name == GUILD:
            break
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name} (id: {guild.id})'
    )
    update_list_lowongan_1hr.start()


@bot.command(name="display")
async def display_list_lowongan(context):
    global data
    if not data:
        response = discord.Embed(
            title=f"There's no lowongan data.",
            description=(
                "Update the data using command `-update`."
            )
        )
    else:
        now = data[0]
        list_lowongan = data[1]
        response = discord.Embed(
            title=f"Ingfo Loker (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
            description=(
                "List lowongan asdos yang buka:\n\n"
                f"{NLINE.join(['• '+text.replace(chr(10), ' ') for text in list_lowongan])}"
            )
        )
    await context.send(embed=response)


@bot.command(name="update")
async def update_list_lowongan(context):
    global data
    new_data = scraper.get_lowongan()
    now = d.datetime.now()
    if not data or set(new_data) != set(data[1]):
        if data:
            new_data_only = list(set(new_data).difference(set(data[1])))
        else:
            new_data_only = new_data
        response = discord.Embed(
            title=f"Lowongan baru unlocked! (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
            description=(
                "List lowongan baru yang telah buka:\n\n"
                f"{NLINE.join(['• '+text.replace(chr(10), ' ') for text in new_data_only])}"
            )
        )
    else:
        response = discord.Embed(
            title=f"Update (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
            description="Belum ada lowongan baru."
        )
    data = (now, new_data)
    write_json(data)
    await context.send(embed=response)


@bot.command(name="h")
async def get_help(context):
    response = discord.Embed(
        title="Bot usage",
        description=(
            "Prefix: -\n\n"
            "Available commands:\n"
            "h : Lists all available commands\n"
            "display : Displays the current lowongan list (might be outdated)\n"
            "update : Updates the lowongan list, displays the difference\n"
        )
    )
    await context.send(embed=response)


@bot.command(name="clear")
async def clear_data(context):
    global data
    data = tuple()
    if os.path.exists("data.json"):
        os.remove("data.json")
    response = discord.Embed(
        title="Data cleared!"
    )
    await context.send(embed=response)


@tasks.loop(minutes=30)
async def update_list_lowongan_1hr():
    global data
    new_data = scraper.get_lowongan()
    now = d.datetime.now()
    if not data:
        response = discord.Embed(
            title=f"Ingfo Loker (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
            description=(
                "List lowongan asdos yang buka:\n\n"
                f"{NLINE.join(['• '+text.replace(chr(10), ' ') for text in new_data])}"
            )
        )
    elif set(new_data) == set(data[1]):
        response = discord.Embed(
            title=f"Update (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
            description="Belum ada lowongan baru."
        )
    else:
        new_data_only = list(set(new_data).difference(set(data[1])))
        response = discord.Embed(
            title=f"Lowongan baru unlocked! (as of {now.strftime('%Y-%m-%d %H:%M:%S')})",
            description=(
                "List lowongan baru yang telah buka:\n\n"
                f"{NLINE.join(['• '+text.replace(chr(10), ' ') for text in new_data_only])}"
            )
        )
    data = (now, new_data)
    write_json(data)
    await bot.get_channel(CHANNEL).send(embed=response)

bot.run(TOKEN)
