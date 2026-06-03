import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

from database.db import log_command, set_afk, remove_afk, get_afk
from services.cv2 import build, error_message, success_message
from utils.checks import can_use_bot


def _format_duration(seconds: float) -> str:
    parts = []
    intervals = [
        ("year", 31536000), ("month", 2592000), ("week", 604800),
        ("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1),
    ]
    remaining = int(seconds)
    for name, secs in intervals:
        count = remaining // secs
        if count:
            parts.append(f"{count} {name}{'s' if count > 1 else ''}")
            remaining %= secs
    return ", ".join(parts) if parts else "a few seconds"


class AfkCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    @app_commands.command(name="afk", description="Set yourself as away from keyboard")
    @app_commands.describe(reason="Reason for going AFK (optional)")
    @app_commands.checks.cooldown(2, 30)
    async def afk(self, interaction: discord.Interaction, reason: str = "") -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=error_message(msg), ephemeral=True)
            return
        if interaction.guild_id is None:
            await interaction.response.send_message(view=error_message("This command can only be used in a server."), ephemeral=True)
            return

        set_afk(interaction.user.id, interaction.guild_id, reason)
        log_command("afk", interaction.user.id, interaction.guild_id)

        display = f"Set AFK{f' — {reason}' if reason else ''}."
        await interaction.response.send_message(view=success_message(display))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        user_id = message.author.id
        guild_id = message.guild.id

        entry = get_afk(user_id, guild_id)
        if entry:
            remove_afk(user_id, guild_id)
            since = entry.get("since", "")
            duration = "unknown"
            if since:
                try:
                    dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                    duration = _format_duration((datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc)).total_seconds())
                except (ValueError, TypeError):
                    pass
            await message.channel.send(
                view=success_message(f"Welcome back! You were AFK for **{duration}**."),
                delete_after=10,
            )
            return

        for mentioned in message.mentions:
            if mentioned.bot:
                continue
            afk_data = get_afk(mentioned.id, guild_id)
            if afk_data:
                since = afk_data.get("since", "")
                reason = afk_data.get("reason", "")
                duration = "unknown"
                if since:
                    try:
                        dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                        duration = _format_duration((datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc)).total_seconds())
                    except (ValueError, TypeError):
                        pass
                parts = [f"**{mentioned.display_name}** is AFK (*{duration}*)"]
                if reason:
                    parts.append(f"> {reason}")
                await message.channel.send(
                    view=build("\n".join(parts), accent_color=0xFEE75C),
                    delete_after=15,
                )
                break


async def setup(client: discord.Client) -> None:
    await client.add_cog(AfkCog(client))
