import discord
from discord import app_commands
from discord.ext import commands
import os
import sys
import logging

from database.db import log_command, get_sync_version, set_sync_version
from services import cv2
from utils.permissions import is_owner

logger = logging.getLogger(__name__)


class OwnerCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_owner(interaction.user.id):
            await interaction.response.send_message(
                view=cv2.error_message("This command is restricted to bot owners."),
                ephemeral=True,
            )
            return False
        return True

    @app_commands.command(name="shutdown", description="Shut down the bot (owner only)")
    async def shutdown(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(view=cv2.info_message("  Shutdown", "Shutting down..."))
        logger.warning("Bot shutdown initiated by %s", interaction.user)
        await self.client.close()

    @app_commands.command(name="restart", description="Restart the bot (owner only)")
    async def restart(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(view=cv2.info_message("  Restart", "Restarting..."))
        logger.warning("Bot restart initiated by %s", interaction.user)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @app_commands.command(name="sync", description="Force sync all slash commands (owner only)")
    async def sync(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.client.tree.sync()
            set_sync_version("__force__")
            await interaction.followup.send(
                view=cv2.success_message(f"Successfully synced `{len(synced)}` command(s) globally."),
                ephemeral=True,
            )
            logger.info("Force sync completed: %d commands", len(synced))
        except Exception as e:
            logger.error("Sync failed: %s", e)
            await interaction.followup.send(
                view=cv2.error_message(f"Sync failed: {e}"),
                ephemeral=True,
            )

    @app_commands.command(name="diagnostics", description="Show bot diagnostics (owner only)")
    async def diagnostics(self, interaction: discord.Interaction) -> None:
        import platform
        await interaction.response.send_message(view=cv2.diagnostics_message(
            uptime="Runtime metrics active",
            latency_ms=round(self.client.latency * 1000),
            guild_count=len(self.client.guilds),
            python_ver=sys.version.split()[0],
            platform_name=platform.system(),
            synced_ver=get_sync_version() or "unknown",
        ))

    @app_commands.command(name="reload", description="Reload all cogs (owner only)")
    async def reload(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            for cog_name in list(self.client.cogs.keys()):
                await self.client.remove_cog(cog_name)

            from cogs.github import GithubCog
            from cogs.utility import UtilityCog
            from cogs.userinfo import UserInfoCog
            from cogs.moderation import ModerationCog
            from cogs.owner import OwnerCog
            from cogs.logs import LogsCog
            from cogs.fun import FunCog
            from cogs.afk import AfkCog
            from cogs.learn import LearnCog

            await self.client.add_cog(GithubCog(self.client))
            await self.client.add_cog(UtilityCog(self.client))
            await self.client.add_cog(UserInfoCog(self.client))
            await self.client.add_cog(ModerationCog(self.client))
            await self.client.add_cog(OwnerCog(self.client))
            await self.client.add_cog(LogsCog(self.client))
            await self.client.add_cog(FunCog(self.client))
            await self.client.add_cog(AfkCog(self.client))
            await self.client.add_cog(LearnCog(self.client))

            logger.info("Cogs reloaded by %s", interaction.user)
            await interaction.followup.send(
                view=cv2.success_message("All cogs reloaded successfully."),
                ephemeral=True,
            )
        except Exception as e:
            logger.error("Reload failed: %s", e)
            await interaction.followup.send(
                view=cv2.error_message(f"Reload failed: {e}"),
                ephemeral=True,
            )


async def setup(client: discord.Client) -> None:
    await client.add_cog(OwnerCog(client))
