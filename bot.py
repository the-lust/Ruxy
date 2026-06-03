#!/usr/bin/env python3
import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
import asyncio

from config import TOKEN, BOT_VERSION, GITHUB_ORG
from database.db import init_db, get_sync_version, set_sync_version, get_log_channels, update_last_sha
from services.logger import setup_logging
from services import github_api, commit_watcher

logger = logging.getLogger(__name__)


class RuxyClient(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = False
        super().__init__(command_prefix="", intents=intents)

    async def setup_hook(self) -> None:
        init_db()
        from cogs.github import setup as gh_setup
        from cogs.utility import setup as ut_setup
        from cogs.userinfo import setup as ui_setup
        from cogs.moderation import setup as mod_setup
        from cogs.owner import setup as own_setup
        from cogs.logs import setup as logs_setup
        from cogs.fun import setup as fun_setup
        from cogs.afk import setup as afk_setup
        from cogs.learn import setup as learn_setup

        await gh_setup(self)
        await ut_setup(self)
        await ui_setup(self)
        await mod_setup(self)
        await own_setup(self)
        await logs_setup(self)
        await fun_setup(self)
        await afk_setup(self)
        await learn_setup(self)

        self.commit_checker.start()
        logger.info("All cogs loaded, commit checker started")

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (ID: %d)", self.user, self.user.id)

        stored = get_sync_version()
        if stored != BOT_VERSION:
            try:
                synced = await self.tree.sync()
                set_sync_version(BOT_VERSION)
                logger.info("Synced %d command(s) to Discord (v%s)", len(synced), BOT_VERSION)
            except Exception as e:
                logger.error("Command sync failed: %s", e)
        else:
            logger.info("Commands already up to date (v%s), skipping sync", BOT_VERSION)

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        from services.cv2 import warning_message, error_message

        if isinstance(error, app_commands.CommandOnCooldown):
            content = warning_message(f"Slow down! Try again in `{error.retry_after:.1f}s`.")
        elif isinstance(error, app_commands.CheckFailure):
            return
        else:
            logger.error("Unhandled error in /%s: %s",
                         interaction.command.name if interaction.command else "?",
                         error)
            content = error_message("An unexpected error occurred. Please try again later.")

        kwargs = {"view": content, "ephemeral": True}
        if not interaction.response.is_done():
            await interaction.response.send_message(**kwargs)
        else:
            await interaction.followup.send(**kwargs)

    @tasks.loop(seconds=120)
    async def commit_checker(self):
        logs = get_log_channels()
        for entry in logs:
            try:
                channel = self.get_channel(entry["channel_id"])
                if not channel:
                    continue
                commits = await github_api.get_commits(entry["repo"], entry["branch"], 3)
                if not commits or not isinstance(commits, list):
                    continue

                for commit in commits:
                    sha = commit["sha"]
                    if sha == entry["last_sha"]:
                        break
                    if entry["last_sha"] == "" or entry["last_sha"] is None:
                        update_last_sha(entry["channel_id"], sha)
                        break
                    full = await github_api.get_commit_detail(commit["url"])
                    if full and isinstance(full, dict):
                        layout = commit_watcher.build_commit_embed(entry["repo"], entry["branch"], full)
                        await channel.send(view=layout)
                    update_last_sha(entry["channel_id"], sha)
            except Exception as e:
                logger.error("Commit check failed for %s: %s", entry["repo"], e)

    @commit_checker.before_loop
    async def before_commit_checker(self):
        await self.wait_until_ready()


client = RuxyClient()

if __name__ == "__main__":
    setup_logging()
    if not TOKEN:
        logger.critical("DISCORD_TOKEN not set. Create a .env file or set the environment variable.")
        raise SystemExit(1)
    client.run(TOKEN)
