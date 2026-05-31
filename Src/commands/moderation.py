import discord
import blacklist
from config import MOD_ROLE_ID, ADMIN_ROLE_ID, MUTE_ROLE_ID
from datetime import timedelta

# only mods and up can use it
# blacklist = can't use the bot
def setup(tree, client):
    @tree.command(
        name="blacklist",
        description="blacklists someone",
    )
    async def blacklist_command(interaction: discord.Interaction, user: discord.Member):
        if not any(role.id in (MOD_ROLE_ID, ADMIN_ROLE_ID) for role in interaction.user.roles):
            await interaction.response.send_message(
                "No permission.",
                ephemeral=True
            )
            return
        if (blacklist.is_blacklisted(user.id)):
            await interaction.response.send_message(user.name + " is already blacklisted")
            return
        
        blacklist.blacklist_user(user.id)


        await interaction.response.send_message(user.name + " has been successfully blacklisted")

    @tree.command(
        name="unblacklist",
        description="Unblacklists someone",
    )
    async def unblacklist_command(
        interaction: discord.Interaction,
        user: discord.Member
    ):
        if not any(role.id in (MOD_ROLE_ID, ADMIN_ROLE_ID)
                for role in interaction.user.roles):
            await interaction.response.send_message(
                "No permission.",
                ephemeral=True
            )
            return

        if not blacklist.is_blacklisted(user.id):
            await interaction.response.send_message(
                f"{user.name} is not blacklisted"
            )
            return

        blacklist.unblacklist_user(user.id)

        await interaction.response.send_message(
            f"{user.name} has been successfully unblacklisted"
        )

    @tree.command(
        name="mute",
        description="Mute a user"
    )
    async def mute(
        interaction: discord.Interaction,
        user: discord.Member,
        minutes: int | None = None
    ):
        author = interaction.user

        if not (
            author.guild_permissions.administrator
            or any(role.id in {MOD_ROLE_ID, ADMIN_ROLE_ID} for role in author.roles)
        ):
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True
            )
            return

        try:
            if minutes is None:
                await user.timeout(
                    timedelta(days=28),
                    reason=f"Muted for 28 days by {author}"
                )

                await interaction.response.send_message(
                    f"{user.mention} has been muted for 28 days."
                )
            else:
                await user.timeout(
                    timedelta(minutes=minutes),
                    reason=f"Muted by {author}"
                )

                await interaction.response.send_message(
                    f"{user.mention} has been muted for {minutes} minute(s)."
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to mute that user.",
                ephemeral=True
            )

    @tree.command(
        name="unmute",
        description="Unmute a user"
    )
    async def unmute(
        interaction: discord.Interaction,
        user: discord.Member
    ):
        author = interaction.user

        if not (
            author.guild_permissions.administrator
            or any(role.id in {MOD_ROLE_ID, ADMIN_ROLE_ID} for role in author.roles)
        ):
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True
            )
            return

        try:
            await user.timeout(
                None,
                reason=f"Unmuted by {author}"
            )

            await interaction.response.send_message(
                f"{user.mention} has been unmuted."
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to unmute that user.",
                ephemeral=True
            )
