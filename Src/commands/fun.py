# SPDX-FileCopyrightText: 2025-present Ahum Maitra theahummaitra@gmail.com
# SPDX-License-Identifier: 	MIT

from discord import Interaction
from datetime import timedelta
import pyjokes
import blacklist
from utility import is_jailed


def setup(tree, client):
    @tree.command(
        name="self-timeout",
        description="Timeout yourself for a specified duration (in minutes)",
    )
    async def self_timeout(interaction: Interaction, duration: int):
        """Allows users to timeout themselves"""

        if duration <= 0:
            await interaction.response.send_message(
                "Invalid request, please enter a valid duration.", ephemeral=True
            )
            return

        if duration > 40320:
            await interaction.response.send_message(
                "You cannot timeout for more than 28 days (40320 minutes).",
                ephemeral=True,
            )
            return

        try:
            await interaction.user.timeout(
                timedelta(minutes=duration),
                reason=f"User-requested timeout for {duration}m",
            )
            await interaction.response.send_message(
                f"Timed out for {duration} minutes."
            )
        except Exception as e:
            await interaction.response.send_message(
                "Failed to apply timeout. Please try again!  **If not working for a long time, contact support team!**", ephemeral=True
            )

    @tree.command(name="joke", description="Get a random joke")
    async def send_joke(interaction: Interaction):
        if blacklist.is_blacklisted(interaction.user.id):
            await interaction.response.send_message("You are blacklisted!")
            return
        elif is_jailed(interaction):
            await interaction.response.send_message("You are in jail!")
            return

        try:
            joke = pyjokes.get_joke()
            await interaction.response.send_message(
                f"**Here's a joke for you:** \n{joke}"
            )
        except Exception as e:
            await interaction.response.send_message(
                "Failed to fetch a joke. Try again later! **If not working for a long time, contact support team!**", ephemeral=True
            )
