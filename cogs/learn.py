import discord
from discord import app_commands
from discord.ext import commands

from database.db import log_command
from services import cv2, ai as ai_service


class LearnCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    @app_commands.command(name="what-is", description="Explain a Rux programming concept")
    @app_commands.describe(concept="The concept to explain (e.g. 'closures', 'generics')")
    @app_commands.checks.cooldown(3, 30)
    async def what_is(self, interaction: discord.Interaction, concept: str) -> None:
        log_command("what-is", interaction.user.id, interaction.guild_id)
        if len(concept) > 500:
            await interaction.response.send_message(view=cv2.error_message("Concept too long (max 500 chars)."), ephemeral=True)
            return

        await interaction.response.defer()
        prompt = f"Explain what `{concept}` is in the Rux programming language. Include a small code snippet showing how it works."
        try:
            answer = await ai_service.ask(prompt)
            view = cv2.build(
                f"## What is {concept}?",
                answer[:1900],
                accent_color=0xA259FF,
            )
            await interaction.followup.send(view=view)
        except RuntimeError as e:
            await interaction.followup.send(view=cv2.error_message(str(e)), ephemeral=True)

    @app_commands.command(name="how-to", description="How to do something in Rux")
    @app_commands.describe(task="The task to accomplish (e.g. 'read a file', 'create a server')")
    @app_commands.checks.cooldown(3, 30)
    async def how_to(self, interaction: discord.Interaction, task: str) -> None:
        log_command("how-to", interaction.user.id, interaction.guild_id)
        if len(task) > 500:
            await interaction.response.send_message(view=cv2.error_message("Task too long (max 500 chars)."), ephemeral=True)
            return

        await interaction.response.defer()
        prompt = f"Show me how to `{task}` in the Rux programming language. Include a complete code snippet."
        try:
            answer = await ai_service.ask(prompt)
            view = cv2.build(
                f"## How to {task}",
                answer[:1900],
                accent_color=0xA259FF,
            )
            await interaction.followup.send(view=view)
        except RuntimeError as e:
            await interaction.followup.send(view=cv2.error_message(str(e)), ephemeral=True)


async def setup(client: discord.Client) -> None:
    await client.add_cog(LearnCog(client))
