import discord
from discord import app_commands
from discord.ext import commands

from config import BOT_NAME, BOT_VERSION, BOT_DESCRIPTION
from database.db import log_command, get_command_stats
from services import cv2
from utils.checks import can_use_bot
from utils.permissions import has_mod_or_admin


class UtilityCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    @app_commands.command(name="ping", description="Check bot latency")
    @app_commands.checks.cooldown(5, 10)
    async def ping(self, interaction: discord.Interaction) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("ping", interaction.user.id, interaction.guild_id)
        latency = round(self.client.latency * 1000)
        await interaction.response.send_message(view=cv2.ping_message(latency))

    @app_commands.command(name="dm", description="Send a direct message to a user")
    @app_commands.describe(user="User to message", message="Message body", reason="Reason shown in the DM")
    @app_commands.checks.cooldown(3, 20)
    async def dm(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        message: str,
        reason: str = "No reason provided",
    ) -> None:
        if not has_mod_or_admin(interaction.user):
            await interaction.response.send_message(view=cv2.error_message("You do not have permission to use this command."), ephemeral=True)
            return
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        if len(message) > 1500 or len(reason) > 300:
            await interaction.response.send_message(view=cv2.error_message("Message or reason is too long."), ephemeral=True)
            return

        log_command("dm", interaction.user.id, interaction.guild_id)
        try:
            await user.send(view=cv2.build(
                "## Message from Ruxy",
                message,
                f"**Reason**\n{reason}",
                footer="Do not reply to this DM.",
            ))
        except discord.Forbidden:
            await interaction.response.send_message(view=cv2.error_message(f"Cannot DM {user.mention}."), ephemeral=True)
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(view=cv2.error_message(f"DM failed: {exc}"), ephemeral=True)
            return

        await interaction.response.send_message(view=cv2.success_message(f"DM sent to {user.mention}."), ephemeral=True)

    @app_commands.command(name="poll", description="Create a poll with up to 10 options")
    @app_commands.describe(
        question="Poll question",
        option1="First option",
        option2="Second option",
        option3="Optional choice",
        option4="Optional choice",
        option5="Optional choice",
        option6="Optional choice",
        option7="Optional choice",
        option8="Optional choice",
        option9="Optional choice",
        option10="Optional choice",
    )
    @app_commands.checks.cooldown(2, 20)
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str | None = None,
        option4: str | None = None,
        option5: str | None = None,
        option6: str | None = None,
        option7: str | None = None,
        option8: str | None = None,
        option9: str | None = None,
        option10: str | None = None,
    ) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return

        options = [option for option in [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10] if option]
        if len({option.lower() for option in options}) != len(options):
            await interaction.response.send_message(view=cv2.error_message("Poll options must be unique."), ephemeral=True)
            return

        labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        body = "\n".join(f"`{labels[index]}.` {option}" for index, option in enumerate(options))

        log_command("poll", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(view=cv2.build(f"## {question}", body, footer=f"Poll by {interaction.user.display_name}"))
        message = await interaction.original_response()
        for reaction in reactions[:len(options)]:
            try:
                await message.add_reaction(reaction)
            except discord.HTTPException:
                break

    @app_commands.command(name="about", description="About Ruxy bot")
    @app_commands.checks.cooldown(3, 10)
    async def about(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(view=cv2.about_message(
            version=BOT_VERSION,
            description=BOT_DESCRIPTION,
            guild_count=len(self.client.guilds),
            latency_ms=round(self.client.latency * 1000),
        ))

    @app_commands.command(name="help", description="Display help for all commands")
    @app_commands.checks.cooldown(3, 10)
    async def help(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(view=cv2.help_message(
            commands_by_category={
                "  Utility": ["ping", "dm", "poll", "about", "help", "stats", "changelog"],
                "  GitHub": ["repo", "contributors", "releases", "issues", "pulls", "packages", "docs"],
                "  Learning": ["what-is", "how-to"],
                "  Fun": ["rps", "joke", "self-timeout", "roast", "rr", "say", "afk"],
                "  User Info": ["userinfo", "whoami", "whois", "serverinfo", "avatar"],
                "  Moderation": ["blacklist", "unblacklist", "whitelist", "mute", "unmute"],
                "  Owner": ["shutdown", "restart", "sync", "reload", "diagnostics"],
            },
            description=f"**{BOT_NAME}** — {BOT_DESCRIPTION}",
        ))

    @app_commands.command(name="stats", description="Bot usage statistics")
    @app_commands.checks.cooldown(2, 15)
    async def stats(self, interaction: discord.Interaction) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("stats", interaction.user.id, interaction.guild_id)
        stats = get_command_stats()
        total = stats["total"]
        top = dict(list(stats["commands"].items())[:10])
        await interaction.response.send_message(view=cv2.stats_message(
            total=total,
            top_commands=top,
            guild_count=len(self.client.guilds),
            latency_ms=round(self.client.latency * 1000),
        ))

    @app_commands.command(name="changelog", description="What's new in this version")
    @app_commands.checks.cooldown(3, 15)
    async def changelog(self, interaction: discord.Interaction) -> None:
        items = [
            "Imported `/poll`, `/dm`, `/whoami`, `/whois`, `/joke`, `/self-timeout`, `/mute`, and `/unmute`",
            "Kept all user-facing command responses on Components V2 containers",
            "Preserved command cooldowns and permission checks",
            "Fixed blacklist persistence during startup",
            "Fixed spam offense tracking persistence",
            "Refined help output and status messages",
        ]
        await interaction.response.send_message(view=cv2.changelog_message(BOT_VERSION, items))


async def setup(client: discord.Client) -> None:
    await client.add_cog(UtilityCog(client))
