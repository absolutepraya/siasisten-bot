# SiAsistenBot

A simple Fasilkom UI's SiAsisten (TA system) scraper to give hourly updates on teaching assistant job vacancies, outputting its result via a Discord bot. Built using Python's `requests` for web interaction, `BeautifulSoup4` for parsing, and `discord.py` for the Discord bot. Uses `python-dotenv` as the environment variable manager.

Uses commands with the prefix `-` to display and update the TA job vacancy list. Not only there are commands to display or update on demand, the program also automatically updates the TA job vacancy every 30 minutes by default.

## Bot Usage

Prefix: `-`

`h`: Lists all available commands

`display`: Displays the currently stored TA job vacancy list (might be outdated)

`update`: Updates the TA job vacancy list, displays the difference.

## Deployment

Here, I assume you have set up your Discord bot, has stored its token, and chosen which Discord server and text channel you want to host the bot in. If you haven't, Google or YouTube it.

If you have, clone the repository to your local machine or virtual private server (preferred, as you can keep the bot running 24/7, even with your computer off):

```
git clone https://github.com/nabilmuafa/SiAsistenBot.git
```

Or, using SSH:

```
git clone git@github.com:nabilmuafa/SiAsistenBot.git
```

Then create a virtual environment using Python, also install the dependencies needed.

Linux:

```
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Windows:

```
python -m venv env
env/Scripts/activate
pip install -r requirements.txt
```

As the scraper and the Discord bot uses `python-dotenv` for environment variables management, you need to create a `.env` file containing the environment variables that will be used in the program. Create a `.env` file containing:

```
DISCORD_TOKEN=<your discord bot token>
DISCORD_GUILD=<your discord server "display name">
DISCORD_CHANNEL=<your discord text channel ID>
SSO_USN=<your UI SSO username>
SSO_PASS=<your UI SSO password, in plaintext>
```

Then, run the program using `docker-compose`:

```
docker-compose up --build -d
```

Or, in newer versions:

```
docker compose up --build -d
```

Your Discord bot should be up and running!

## Known issues:

- Time zones cannot be localized, will always display time zone according to the deployment device's time zone (if your system is UTC+0 but you're living in UTC+7, for example, the time displayed will still be in UTC+0).
