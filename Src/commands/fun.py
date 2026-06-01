# SPDX-FileCopyrightText: 2025-present Ahum Maitra theahummaitra@gmail.com
# SPDX-License-Identifier: 	MIT

from discord import Interaction
from datetime import timedelta

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
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)
