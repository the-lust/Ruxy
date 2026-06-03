import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta

from database.db import blacklist_add, blacklist_remove, is_blacklisted, log_command
from services import cv2
from utils.permissions import has_mod_or_admin


class ModerationCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    @app_commands.command(
        name="blacklist",
        description="Blacklist a user from using the bot",
    )
    @app_commands.describe(
        user="The user to blacklist",
        reason="Reason for blacklisting",
        duration="Duration in minutes (leave empty for permanent)",
    )
    @app_commands.checks.cooldown(5, 10)
    async def blacklist(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided",
        duration: int | None = None,
    ) -> None:
        if not has_mod_or_admin(interaction.user):
            await interaction.response.send_message(
                view=cv2.error_message("You do not have permission to use this command."),
                ephemeral=True,
            )
            return
        if is_blacklisted(user.id):
            await interaction.response.send_message(
                view=cv2.warning_message(f"{user.mention} is already blacklisted."),
                ephemeral=True,
            )
            return

        blacklist_add(user.id, reason, interaction.user.id, duration_mins=duration)
        log_command("blacklist", interaction.user.id, interaction.guild_id)

        dur_str = f"{duration} minutes" if duration else "Permanent"
        await interaction.response.send_message(
            view=cv2.build(
                f"## Blacklist Applied\n"
                f"• **User** {user.mention}\n"
                f"• **Reason** {reason}\n"
                f"• **Duration** `{dur_str}`",
                accent_color=0x57F287,
            )
        )

    @app_commands.command(name="unblacklist", description="Remove a user from the blacklist")
    @app_commands.describe(user="The user to unblacklist")
    @app_commands.checks.cooldown(5, 10)
    async def unblacklist(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        if not has_mod_or_admin(interaction.user):
            await interaction.response.send_message(
                view=cv2.error_message("You do not have permission to use this command."),
                ephemeral=True,
            )
            return

        if not is_blacklisted(user.id):
            await interaction.response.send_message(
                view=cv2.warning_message(f"{user.mention} is not blacklisted."),
                ephemeral=True,
            )
            return

        blacklist_remove(user.id)
        log_command("unblacklist", interaction.user.id, interaction.guild_id)

        await interaction.response.send_message(
            view=cv2.success_message(f"{user.mention} has been successfully unblacklisted."),
        )

    @app_commands.command(name="whitelist", description="Remove a permanent blacklist (manual override)")
    @app_commands.describe(user="The user to whitelist")
    @app_commands.checks.cooldown(5, 10)
    async def whitelist(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        if not has_mod_or_admin(interaction.user):
            await interaction.response.send_message(
                view=cv2.error_message("You do not have permission to use this command."),
                ephemeral=True,
            )
            return

        blacklist_remove(user.id)
        log_command("whitelist", interaction.user.id, interaction.guild_id)

        await interaction.response.send_message(
            view=cv2.success_message(f"{user.mention} has been whitelisted."),
        )

    @app_commands.command(name="mute", description="Timeout a user")
    @app_commands.describe(user="The user to timeout", minutes="Duration in minutes, defaults to 40320")
    @app_commands.checks.cooldown(3, 10)
    async def mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        minutes: int | None = None,
    ) -> None:
        is_admin = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator
        if not has_mod_or_admin(interaction.user) and not is_admin:
            await interaction.response.send_message(
                view=cv2.error_message("You do not have permission to use this command."),
                ephemeral=True,
            )
            return
        duration = 40320 if minutes is None else minutes
        if duration <= 0 or duration > 40320:
            await interaction.response.send_message(
                view=cv2.error_message("Mute duration must be between 1 and 40320 minutes."),
                ephemeral=True,
            )
            return
        if user.id == interaction.user.id:
            await interaction.response.send_message(view=cv2.error_message("Use `/self-timeout` for yourself."), ephemeral=True)
            return

        try:
            await user.timeout(timedelta(minutes=duration), reason=f"Muted by {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(view=cv2.error_message("I cannot mute that user."), ephemeral=True)
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(view=cv2.error_message(f"Mute failed: {exc}"), ephemeral=True)
            return

        log_command("mute", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(view=cv2.success_message(f"{user.mention} has been muted for `{duration}` minute(s)."))

    @app_commands.command(name="unmute", description="Remove a user's timeout")
    @app_commands.describe(user="The user to unmute")
    @app_commands.checks.cooldown(3, 10)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member) -> None:
        is_admin = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator
        if not has_mod_or_admin(interaction.user) and not is_admin:
            await interaction.response.send_message(
                view=cv2.error_message("You do not have permission to use this command."),
                ephemeral=True,
            )
            return
        try:
            await user.timeout(None, reason=f"Unmuted by {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(view=cv2.error_message("I cannot unmute that user."), ephemeral=True)
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(view=cv2.error_message(f"Unmute failed: {exc}"), ephemeral=True)
            return

        log_command("unmute", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(view=cv2.success_message(f"{user.mention} has been unmuted."))


async def setup(client: discord.Client) -> None:
    await client.add_cog(ModerationCog(client))
