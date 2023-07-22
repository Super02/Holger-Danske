import os
from random import choice
from nextcord import Intents
from nextcord.ext import commands
from string import ascii_lowercase
import traceback
from cogwatch import Watcher
import nextcord
import random
import utils
import sentry_sdk
from nextcord.ext import tasks

intents = Intents.all()
bot = commands.Bot(command_prefix=''.join([choice(ascii_lowercase) for _ in range(32)]), intents=intents)

# Load sentry
print("Loading sentry...")
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    traces_sample_rate=1.0,
)
print("Loaded sentry")

# Load cogs
for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        try:
            bot.load_extension(f'cogs.{filename[:-3]}')
        except Exception as e:
            print(f'Failed to load {filename[:-3]} with error: {traceback.format_exc()}')
        print(f"Loaded {filename[:-3]}")

@bot.event
async def on_error(event, *args, **kwargs):
    """Don't ignore the error, causing Sentry to capture it."""
    raise

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}#{bot.user.discriminator} ({bot.user.id})")
    await update_status()
    update_status.start()
    watcher = Watcher(bot, path='cogs', preload=True, debug=True)
    await watcher.start()

@tasks.loop(hours=2)
async def update_status():
    await utils.Utils().update_status(bot)

bot.run(os.getenv('TOKEN'))
