import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

from database.db import log_command, add_log_channel, remove_log_channel, get_log_channels
from services import github_api
from utils.permissions import has_mod_or_admin
from config import BOT_COLOR, BOT_NAME, BOT_VERSION


def _embed(description: str, color: int = BOT_COLOR) -> discord.Embed:
    e = discord.Embed(description=description, color=color, timestamp=datetime.now(timezone.utc))
    e.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
    return e


class LogsCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    @app_commands.command(name="set-log", description="Watch a repo for new commits (posts to this channel)")
    @app_commands.describe(repository="Repository name", branch="Branch to watch (default: main)")
    @app_commands.checks.cooldown(3, 30)
    async def set_log(
        self,
        interaction: discord.Interaction,
        repository: str,
        branch: str = "main",
    ) -> None:
        if not has_mod_or_admin(interaction.user):
            await interaction.response.send_message(
                embed=_embed("## Error\nNo permission.", color=0xED4245), ephemeral=True
            )
            return

        info = await github_api.get_repo(repository)
        if not info:
            await interaction.response.send_message(
                embed=_embed(f"## Error\nRepository `{repository}` not found.", color=0xED4245),
                ephemeral=True,
            )
            return

        branch_ok = await github_api.branch_exists(repository, branch)
        if not branch_ok:
            await interaction.response.send_message(
                embed=_embed(f"## Error\nBranch `{branch}` not found in `{repository}`.", color=0xED4245),
                ephemeral=True,
            )
            return

        add_log_channel(interaction.channel_id, repository, branch)
        log_command("set-log", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(
            embed=_embed(
                f"## Log Set\nThis channel will now receive commit updates for **{repository}/{branch}**.",
                color=0x57F287,
            )
        )

    @app_commands.command(name="remove-log", description="Stop watching a repo in this channel")
    @app_commands.checks.cooldown(3, 10)
    async def remove_log(self, interaction: discord.Interaction) -> None:
        if not has_mod_or_admin(interaction.user):
            await interaction.response.send_message(
                embed=_embed("## Error\nNo permission.", color=0xED4245), ephemeral=True
            )
            return

        remove_log_channel(interaction.channel_id)
        log_command("remove-log", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(
            embed=_embed("## Log Removed\nThis channel will no longer receive commit updates.", color=0x57F287)
        )

    @app_commands.command(name="list-logs", description="List all watched repos")
    @app_commands.checks.cooldown(3, 10)
    async def list_logs(self, interaction: discord.Interaction) -> None:
        if not has_mod_or_admin(interaction.user):
            await interaction.response.send_message(
                embed=_embed("## Error\nNo permission.", color=0xED4245), ephemeral=True
            )
            return

        logs = get_log_channels()
        if not logs:
            await interaction.response.send_message(
                embed=_embed("## Watched Repositories\nNo repositories are being watched.")
            )
            return

        lines = []
        for l in logs:
            channel = self.client.get_channel(l["channel_id"])
            ch = f"<#{l['channel_id']}>" if not channel else channel.mention
            line = f"• `{l['repo']}/{l['branch']}`  →  {ch}"
            if l["last_sha"]:
                line += f"  (`{l['last_sha'][:7]}`)"
            lines.append(line)

        await interaction.response.send_message(
            embed=_embed("## Watched Repositories\n" + "\n".join(lines))
        )


async def setup(client: discord.Client) -> None:
    await client.add_cog(LogsCog(client))
