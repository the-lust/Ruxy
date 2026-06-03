import discord
from discord import app_commands
from discord.ext import commands

from database.db import log_command
from services import cv2
from utils.checks import can_use_bot


class UserInfoCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    @app_commands.command(name="userinfo", description="Display information about a user")
    @app_commands.describe(user="The user to look up (leave empty for yourself)")
    @app_commands.checks.cooldown(3, 10)
    async def userinfo(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("userinfo", interaction.user.id, interaction.guild_id)
        target = user or interaction.user
        await interaction.response.send_message(view=cv2.profile_message(target))

    @app_commands.command(name="whoami", description="Display information about yourself")
    @app_commands.checks.cooldown(3, 10)
    async def whoami(self, interaction: discord.Interaction) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(view=cv2.error_message("This command must be used in a server."), ephemeral=True)
            return
        log_command("whoami", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(view=cv2.profile_message(interaction.user))

    @app_commands.command(name="whois", description="Display information about another user")
    @app_commands.describe(user="The user to look up")
    @app_commands.checks.cooldown(3, 10)
    async def whois(self, interaction: discord.Interaction, user: discord.Member) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("whois", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(view=cv2.profile_message(user))

    @app_commands.command(name="serverinfo", description="Display information about this server")
    @app_commands.checks.cooldown(3, 15)
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("serverinfo", interaction.user.id, interaction.guild_id)
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(view=cv2.error_message("This command must be used in a server."))
            return
        await interaction.response.send_message(view=cv2.server_message(guild))

    @app_commands.command(name="avatar", description="Get a user's avatar")
    @app_commands.describe(user="The user whose avatar to fetch (leave empty for yourself)")
    @app_commands.checks.cooldown(5, 5)
    async def avatar(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("avatar", interaction.user.id, interaction.guild_id)
        target = user or interaction.user
        await interaction.response.send_message(view=cv2.avatar_message(target))


async def setup(client: discord.Client) -> None:
    await client.add_cog(UserInfoCog(client))
