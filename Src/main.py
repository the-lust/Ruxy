import discord
from discord import app_commands
from discord.ext import commands
from config import TOKEN

from commands import utility
from commands import user
from commands import github
from commands import owner
from commands import moderation
from commands import fun
from commands import poll


class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.synced = False

    async def setup_hook(self):
        print(self.guilds)
        if self.synced:
            print("setup_hook failed - already synced")
            return
        for guild in self.guilds:
            try:
                synced = await self.tree.sync(guild=guild)
                print(
                    f"Instantly synced {len(synced)} command(s) "
                    f"to guild: {guild.name}"
                )
            except Exception as e:
                print(
                    f"Failed to sync to guild "
                    f"{guild.name}: {e}"
                )
    
            self.synced = True 

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        await self.setup_hook()


intents = discord.Intents.default()

client = Client(
    intents=intents
)

tree = app_commands.CommandTree(client)

utility.setup(tree, client)
user.setup(tree, client)
github.setup(tree, client)
owner.setup(tree, client)
moderation.setup(tree, client)
fun.setup(tree, client)
poll.setup(tree, client)

client.run(TOKEN)