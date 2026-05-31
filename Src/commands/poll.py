import discord
from discord import app_commands
import asyncio
import datetime
import pytz
import blacklist
from utility import is_jailed

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

active_polls: dict[int, datetime.datetime] = {}
poll_options: dict[int, list[str]] = {}
poll_channels: dict[int, int] = {}


async def _expire_poll(client: discord.Client, message_id: int, channel_id: int, options: list[str], delay: float):
    await asyncio.sleep(delay)

    if message_id not in active_polls:
        return

    channel = client.get_channel(channel_id)
    if channel is None:
        active_polls.pop(message_id, None)
        poll_options.pop(message_id, None)
        poll_channels.pop(message_id, None)
        return

    try:
        message = await channel.fetch_message(message_id)
    except (discord.NotFound, discord.Forbidden):
        active_polls.pop(message_id, None)
        poll_options.pop(message_id, None)
        poll_channels.pop(message_id, None)
        return

    total_votes = 0
    vote_counts = []

    for i in range(len(options)):
        reaction = discord.utils.get(message.reactions, emoji=NUMBER_EMOJIS[i])
        count = (reaction.count - 1) if reaction else 0
        vote_counts.append(count)
        total_votes += count

    try:
        await message.clear_reactions()
    except discord.Forbidden:
        pass

    if total_votes > 0:
        max_votes = max(vote_counts)
        winning_indices = [i for i, c in enumerate(vote_counts) if c == max_votes]

        if len(winning_indices) == 1:
            idx = winning_indices[0]
            percentage = (vote_counts[idx] / total_votes) * 100
            result_embed = discord.Embed(
                title="Poll Ended",
                description=(
                    f"**{options[idx]}** won with **{percentage:.1f}%** of total votes "
                    f"({vote_counts[idx]}/{total_votes} votes)"
                ),
                color=discord.Color.green(),
                timestamp=datetime.datetime.now(),
            )
        else:
            winners = ", ".join(options[i] for i in winning_indices)
            percentage = (max_votes / total_votes) * 100
            result_embed = discord.Embed(
                title="Poll Ended",
                description=(
                    f"**Tie!** {winners} tied with **{percentage:.1f}%** of total votes "
                    f"({max_votes}/{total_votes} votes each)"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.datetime.now(),
            )
    else:
        result_embed = discord.Embed(
            title="Poll Ended",
            description="No votes were cast.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(),
        )

    try:
        await channel.send(embed=result_embed)
    except discord.Forbidden:
        pass

    active_polls.pop(message_id, None)
    poll_options.pop(message_id, None)
    poll_channels.pop(message_id, None)


def setup(tree, client):
    @tree.command(
        name="poll",
        description="Create a poll with multiple options"
    )
    @app_commands.describe(
        question="The poll question",
        options="Poll options separated by ' | ' (max 10 options)",
        end_after="Optional: End date and time (MM/DD/YY HH:MMAM/PM) in EST",
    )
    async def poll(
        interaction: discord.Interaction,
        question: str,
        options: str,
        end_after: str = None,
    ):
        if blacklist.is_blacklisted(interaction.user.id):
            await interaction.response.send_message("You are blacklisted")
            return
        elif is_jailed(interaction):
            await interaction.response.send_message("You are in jail")
            return

        option_list = [opt.strip() for opt in options.split("|")]

        if len(option_list) < 2:
            await interaction.response.send_message(
                "Please provide at least 2 options separated by ' | '",
                ephemeral=True
            )
            return

        if len(option_list) > 10:
            await interaction.response.send_message(
                "Maximum 10 options allowed!",
                ephemeral=True
            )
            return

        end_time = None
        if end_after:
            try:
                est = pytz.timezone("America/New_York")
                end_time = datetime.datetime.strptime(end_after, "%m/%d/%y %I:%M%p")
                end_time = est.localize(end_time)

                now = datetime.datetime.now(est)
                if end_time <= now:
                    await interaction.response.send_message(
                        "End time must be in the future!",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    "Invalid date format! Use MM/DD/YY HH:MMAM/PM (e.g., 4/4/26 5:00PM)",
                    ephemeral=True
                )
                return

        poll_text = f"**{question}**\n\n"
        for i, option in enumerate(option_list):
            poll_text += f"{NUMBER_EMOJIS[i]}: {option}\n"

        embed = discord.Embed(
            title="Poll",
            description=poll_text,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Poll created by {interaction.user.display_name}")

        if end_time:
            embed.add_field(
                name="Ends",
                value=end_time.strftime("%m/%d/%y %I:%M%p EST"),
                inline=False
            )

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        for i in range(len(option_list)):
            await message.add_reaction(NUMBER_EMOJIS[i])

        if end_time:
            now = datetime.datetime.now(pytz.timezone("America/New_York"))
            delay = (end_time - now).total_seconds()

            active_polls[message.id] = end_time
            poll_options[message.id] = option_list
            poll_channels[message.id] = interaction.channel_id

            asyncio.get_event_loop().create_task(
                _expire_poll(client, message.id, interaction.channel_id, option_list, delay)
            )