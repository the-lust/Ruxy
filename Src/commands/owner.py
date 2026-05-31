import discord
from discord import app_commands
import os
import sys
from config import MOD_ROLE_ID, ADMIN_ROLE_ID

from config import OWNERS


def setup(tree, client):
    @tree.command(
        name="shutdown",
        description="Shuts down Ruxy"
    )
    async def shutdown(interaction: discord.Interaction):
        if interaction.user.id not in OWNERS:
            await interaction.response.send_message(
                "You cannot use this command.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Shutting down...",
            ephemeral=True
        )

        await client.close()

    @tree.command(
        name="restart",
        description="Restarts Ruxy"
    )
    async def restart(interaction: discord.Interaction):
        if interaction.user.id not in OWNERS:
            await interaction.response.send_message(
                "You cannot use this command.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Restarting...",
            ephemeral=True
        )

        os.execv(
            sys.executable,
            [sys.executable] + sys.argv
        )