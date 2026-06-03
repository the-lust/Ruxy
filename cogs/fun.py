import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import LayoutView, ActionRow, Button, Container, TextDisplay
from discord import ButtonStyle
from datetime import timedelta
import random

from database.db import log_command
from services import cv2
from utils.checks import can_use_bot


ROASTS = [
    "{user}, you're not stupid; you just have bad luck thinking.",
    "I'd agree with you {user}, but then we'd both be wrong.",
    "{user}, you're the human equivalent of a TypeError.",
    "If {user} were any more of a bottleneck, they'd be a bottle factory.",
    "{user}, you have the perfect face for radio.",
    "Roses are red, violets are blue, {user}, I have 5 lines in this roast and I can't think of one for you.",
    "{user} is living proof that you can't fix stupid.",
    "Somewhere out there, {user}, a tree is working hard to produce the oxygen you're wasting.",
    "I'd call {user} a tool, but that would imply they're useful for something.",
    "If {user}'s brain was JSON, it would be full of syntax errors.",
]

JOKES = [
    "A programmer walks into a bar, orders 1.000000 round, and leaves because of a floating point issue.",
    "I would tell you a UDP joke, but you might not get it.",
    "There are only two hard things in programming: cache invalidation, naming things, and off-by-one errors.",
    "A SQL query walks into a bar and sees two tables. It asks, 'May I join you?'",
    "The compiler said no, but the runtime said maybe.",
    "I renamed my variable to `done`; now the code feels complete.",
]

CHOICES = {"\U0001f44a": "Rock", "\U0000270b": "Paper", "\U0000270c": "Scissors"}
EMOJI = {"Rock": "\U0001f44a", "Paper": "\U0000270b", "Scissors": "\U0000270c"}


class RPSView(LayoutView):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.result_sent = False
        container = Container(TextDisplay("## Rock Paper Scissors\n\nChoose your move!"), accent_color=0xA259FF)
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return False
        return True

    async def _disable_all(self):
        for child in self.walk_children():
            if isinstance(child, Button):
                child.disabled = True

    async def _play(self, interaction: discord.Interaction, player_choice: str):
        self.result_sent = True
        bot_choice = random.choice(["Rock", "Paper", "Scissors"])
        if player_choice == bot_choice:
            result, color = "It's a **tie**!", 0xFEE75C
        elif (
            (player_choice == "Rock" and bot_choice == "Scissors") or
            (player_choice == "Paper" and bot_choice == "Rock") or
            (player_choice == "Scissors" and bot_choice == "Paper")
        ):
            result, color = "You **win**!", 0x57F287
        else:
            result, color = "You **lose**!", 0xED4245
        await self._disable_all()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            view=cv2.build(
                f"## Rock Paper Scissors\n\n"
                f"You chose {EMOJI[player_choice]} **{player_choice}**\n"
                f"Bot chose {EMOJI[bot_choice]} **{bot_choice}**\n\n"
                f"### {result}",
                accent_color=color,
            )
        )

    action_row = ActionRow()

    @action_row.button(style=ButtonStyle.primary, emoji="\U0001f44a", label="Rock")
    async def rock(self, interaction: discord.Interaction, button: Button):
        await self._play(interaction, "Rock")

    @action_row.button(style=ButtonStyle.success, emoji="\U0000270b", label="Paper")
    async def paper(self, interaction: discord.Interaction, button: Button):
        await self._play(interaction, "Paper")

    @action_row.button(style=ButtonStyle.danger, emoji="\U0000270c", label="Scissors")
    async def scissors(self, interaction: discord.Interaction, button: Button):
        await self._play(interaction, "Scissors")


class RRView(LayoutView):
    def __init__(self, interaction: discord.Interaction, members: list[discord.Member]):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.members = members
        self.num_players = len(members)
        self.bullet = random.randint(0, 5)
        self.pull_count = 0
        self.current_index = 0
        self.game_over = False
        self._rebuild()

    def _chambers_display(self) -> str:
        return " ".join(
            "\U0001f4a5" if (i == self.bullet and self.game_over and i < self.pull_count) else
            "\U0001f52b" if (i < self.pull_count) else
            "\U000026ab"
            for i in range(6)
        )

    def _rebuild(self):
        self.clear_items()
        chambers = self._chambers_display()
        if self.game_over:
            status = f"## Russian Roulette\n{chambers}\n\n**Game Over**"
        else:
            current = self.members[self.current_index]
            status = f"## Russian Roulette\n{chambers}\n\n**Turn:** {current.mention}  (`{self.pull_count}/6` pulled)"
        self.add_item(Container(TextDisplay(status), accent_color=0xED4245 if self.game_over else 0xA259FF))
        if not self.game_over:
            btn = Button(style=ButtonStyle.danger, emoji="\U0001f52b", label="  Pull the Trigger!")
            btn.callback = self._on_pull
            row = ActionRow()
            row.add_item(btn)
            self.add_item(row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.game_over:
            await interaction.response.send_message("Game is over.", ephemeral=True)
            return False
        if interaction.user.id != self.members[self.current_index].id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return False
        return True

    async def _on_pull(self, interaction: discord.Interaction):
        hit = (self.pull_count == self.bullet)
        self.pull_count += 1

        if hit:
            self.game_over = True
            victim = self.members[self.current_index]
            self._rebuild()
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                view=cv2.build(
                    f"## \U0001f480 BANG!\n\n{victim.mention} took the bullet!",
                    accent_color=0xED4245,
                )
            )
        elif self.pull_count >= 6:
            self.game_over = True
            self._rebuild()
            await interaction.response.edit_message(view=self)
            survivors = ", ".join(m.mention for m in self.members)
            await interaction.followup.send(
                view=cv2.build(
                    f"## \U0001f389 Everyone Survived!\n\nAll 6 chambers were clear!\n{survivors}",
                    accent_color=0x57F287,
                )
            )
        else:
            self.current_index = (self.current_index + 1) % self.num_players
            self._rebuild()
            await interaction.response.edit_message(view=self)
            next_player = self.members[self.current_index]
            await interaction.followup.send(
                view=cv2.build(
                    f"## \U0001f605 Click!\n\nSafe... **{next_player.display_name}**, you're up!",
                    accent_color=0xFEE75C,
                )
            )


class FunCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    @app_commands.command(name="self-timeout", description="Timeout yourself for a duration in minutes")
    @app_commands.describe(duration="Duration in minutes, max 40320")
    @app_commands.checks.cooldown(2, 30)
    async def self_timeout(self, interaction: discord.Interaction, duration: int) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(view=cv2.error_message("This command must be used in a server."), ephemeral=True)
            return
        if duration <= 0:
            await interaction.response.send_message(view=cv2.error_message("Duration must be greater than zero."), ephemeral=True)
            return
        if duration > 40320:
            await interaction.response.send_message(view=cv2.error_message("Maximum self-timeout is 40320 minutes."), ephemeral=True)
            return

        try:
            await interaction.user.timeout(timedelta(minutes=duration), reason=f"Self-timeout for {duration} minutes")
        except discord.Forbidden:
            await interaction.response.send_message(view=cv2.error_message("I cannot timeout your account in this server."), ephemeral=True)
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(view=cv2.error_message(f"Timeout failed: {exc}"), ephemeral=True)
            return

        log_command("self-timeout", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(view=cv2.success_message(f"Timed out for `{duration}` minute(s)."), ephemeral=True)

    @app_commands.command(name="joke", description="Get a random programming joke")
    @app_commands.checks.cooldown(3, 10)
    async def joke(self, interaction: discord.Interaction) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("joke", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(view=cv2.build("## Joke", random.choice(JOKES)))

    @app_commands.command(name="rps", description="Play Rock Paper Scissors against the bot")
    @app_commands.checks.cooldown(3, 10)
    async def rps(self, interaction: discord.Interaction) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("rps", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(view=RPSView(interaction))

    @app_commands.command(name="roast", description="Roast a member")
    @app_commands.describe(member="The member to roast")
    @app_commands.checks.cooldown(3, 20)
    async def roast(self, interaction: discord.Interaction, member: discord.Member) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("roast", interaction.user.id, interaction.guild_id)
        roast = random.choice(ROASTS).format(user=member.mention)
        await interaction.response.send_message(view=cv2.build(f"## Roast\n{roast}", accent_color=0xED4245))

    @app_commands.command(name="rr", description="Play Russian Roulette with 1-6 players")
    @app_commands.describe(
        p1="Player 1 (optional)",
        p2="Player 2 (optional)",
        p3="Player 3 (optional)",
        p4="Player 4 (optional)",
        p5="Player 5 (optional)",
    )
    @app_commands.checks.cooldown(3, 15)
    async def rr(
        self,
        interaction: discord.Interaction,
        p1: discord.Member | None = None,
        p2: discord.Member | None = None,
        p3: discord.Member | None = None,
        p4: discord.Member | None = None,
        p5: discord.Member | None = None,
    ) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        log_command("rr", interaction.user.id, interaction.guild_id)

        members = [interaction.user]
        for p in [p1, p2, p3, p4, p5]:
            if p and p.id not in [m.id for m in members]:
                members.append(p)

        if len(members) > 6:
            await interaction.response.send_message(view=cv2.error_message("Maximum 6 players allowed."), ephemeral=True)
            return

        names = ", ".join(m.mention for m in members)
        await interaction.response.send_message(
            view=cv2.build(
                f"## Russian Roulette\n\n**Players ({len(members)}):** {names}\n\n*6 chambers, 1 bullet...*",
                accent_color=0xED4245,
            )
        )
        await interaction.followup.send(view=RRView(interaction, members))

    @app_commands.command(name="say", description="Make the bot say something")
    @app_commands.describe(text="What to say")
    @app_commands.checks.cooldown(5, 10)
    async def say(self, interaction: discord.Interaction, text: str) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return
        if len(text) > 1900:
            await interaction.response.send_message(view=cv2.error_message("Message too long (max 1900 chars)."), ephemeral=True)
            return
        log_command("say", interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(view=cv2.build(f"## {interaction.user.display_name} says\n{text}"))


async def setup(client: discord.Client) -> None:
    await client.add_cog(FunCog(client))
