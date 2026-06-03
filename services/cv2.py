import discord
from discord import ButtonStyle
from discord.enums import SeparatorSpacing
from discord.ui import ActionRow, Button, Container, LayoutView, Section, Separator, TextDisplay, Thumbnail

from config import BOT_NAME, BOT_VERSION


BADGE_EMOJIS: dict[str, str] = {
    "staff": "<:discordstaff:314068430847893504>",
    "partner": "<:discordpartner:314068430879653888>",
    "hypesquad": "<:hypesquadevents:585765895939424258>",
    "bug_hunter": "<:bughunter1:585765895757078526>",
    "hypesquad_bravery": "<:hypesquadbravery:585765895730376714>",
    "hypesquad_brilliance": "<:hypesquadbrilliance:585765895736143536>",
    "hypesquad_balance": "<:hypesquadbalance:585765895719559178>",
    "early_supporter": "<:earlysupporter:585765895155859456>",
    "bug_hunter_level_2": "<:bughunter2:585765895745601536>",
    "verified_bot_developer": "<:botdev:585765895769530378>",
    "discord_certified_moderator": "<:certifiedmod:817475310735327262>",
    "active_developer": "<:activedev:1040460695227793539>",
    "verified_bot": "<:verifiedbot:585765895769530378>",
    "bot_http_interactions": "<:supportscommands:585765895939424258>",
}


def _view(items: list, accent_color: int = 0xA259FF) -> LayoutView:
    view = LayoutView(timeout=180)
    view.add_item(Container(*items, accent_color=accent_color))
    return view


def _parts(*texts: str) -> list:
    items: list = []
    for text in texts:
        if not text:
            continue
        if items:
            items.append(Separator(spacing=SeparatorSpacing.small))
        items.append(TextDisplay(text))
    return items


def _badges(flags: discord.PublicUserFlags) -> str:
    return " ".join(emoji for attr, emoji in BADGE_EMOJIS.items() if getattr(flags, attr, False))


def build(
    *texts: str,
    accent_color: int = 0xA259FF,
    thumbnail_url: str | None = None,
    footer: str | None = None,
) -> LayoutView:
    items: list = []
    body = list(texts)
    if thumbnail_url:
        first = body.pop(0) if body else "\u200b"
        items.append(Section(TextDisplay(first), accessory=Thumbnail(thumbnail_url)))
    items.extend(_parts(*body))
    if footer:
        if items:
            items.append(Separator(spacing=SeparatorSpacing.small))
        items.append(TextDisplay(f"-# {footer}"))
    return _view(items or [TextDisplay("\u200b")], accent_color)


def error_message(msg: str) -> LayoutView:
    return build(f"## Error\n> {msg}", accent_color=0xED4245)


def success_message(msg: str) -> LayoutView:
    return build(f"## Success\n> {msg}", accent_color=0x57F287)


def warning_message(msg: str) -> LayoutView:
    return build(f"## Warning\n> {msg}", accent_color=0xFEE75C)


def info_message(title: str, desc: str) -> LayoutView:
    return build(f"## {title}\n> {desc}")


def ping_message(latency_ms: int) -> LayoutView:
    return build(f"## Pong\nGateway latency: `{latency_ms}ms`")


def about_message(version: str, description: str, guild_count: int, latency_ms: int) -> LayoutView:
    return build(
        f"## {BOT_NAME} v{version}",
        f"> {description}",
        f"**Servers** `{guild_count:,}`  |  **Latency** `{latency_ms}ms`",
        footer=f"{BOT_NAME} v{BOT_VERSION}  |  /help for commands",
    )


def help_message(commands_by_category: dict[str, list[str]], description: str = "") -> LayoutView:
    total = sum(len(commands) for commands in commands_by_category.values())
    blocks = [f"## {BOT_NAME} Commands\n> {description}"]
    for category, commands in commands_by_category.items():
        blocks.append(f"### {category}\n" + " ".join(f"`/{command}`" for command in commands))
    return build(*blocks, footer=f"{BOT_NAME} v{BOT_VERSION}  |  {total} commands")


def stats_message(total: int, top_commands: dict, guild_count: int, latency_ms: int) -> LayoutView:
    blocks = [f"## Bot Statistics\n**Total Executions** `{total:,}`"]
    if top_commands:
        rows = "\n".join(f"- `/{name}`: **{count:,}**" for name, count in top_commands.items())
        blocks.append(f"### Top Commands\n{rows}")
    blocks.append(f"**Servers** `{guild_count:,}`  |  **Latency** `{latency_ms}ms`")
    return build(*blocks)


def diagnostics_message(
    uptime: str,
    latency_ms: int,
    guild_count: int,
    python_ver: str,
    platform_name: str,
    synced_ver: str,
) -> LayoutView:
    return build(
        "## Diagnostics",
        f"**Uptime** {uptime}  |  **Latency** `{latency_ms}ms`",
        f"**Servers** `{guild_count:,}`  |  **Python** `{python_ver}`",
        f"**Platform** `{platform_name}`  |  **Sync** `{synced_ver}`",
    )


def changelog_message(version: str, items: list[str]) -> LayoutView:
    return build(f"## {BOT_NAME} v{version}", "\n".join(f"- {item.strip()}" for item in items))


def packages_message(packages: dict) -> LayoutView:
    rows = "\n".join(f"- `{name}`: [{url.split('/')[-1]}]({url})" for name, url in sorted(packages.items()))
    return build(
        "## Rux Ecosystem",
        "> Core repositories in the Rux programming language ecosystem.",
        f"### Available Packages\n{rows}",
    )


def profile_message(user: discord.Member) -> LayoutView:
    created = discord.utils.format_dt(user.created_at, style="F")
    created_rel = discord.utils.format_dt(user.created_at, style="R")
    lines = [
        f"- **Username** {user.name}",
        f"- **Nickname** {user.nick or '-'}",
        f"- **Created** {created} ({created_rel})",
    ]
    if user.joined_at:
        joined = discord.utils.format_dt(user.joined_at, style="F")
        joined_rel = discord.utils.format_dt(user.joined_at, style="R")
        lines.append(f"- **Joined Server** {joined} ({joined_rel})")
    roles = [role.mention for role in user.roles if role.name != "@everyone"]
    if roles:
        shown = " ".join(roles[:10])
        if len(roles) > 10:
            shown += f" *+{len(roles) - 10} more*"
        lines.append(f"\n**Roles ({len(roles)})**\n{shown}")
    badges = _badges(user.public_flags)
    if badges:
        lines.append(f"\n**Badges** {badges}")
    return _view([
        Section(TextDisplay(f"## {user.display_name}\n`{user.id}`"), accessory=Thumbnail(user.display_avatar.url)),
        Separator(spacing=SeparatorSpacing.small),
        TextDisplay("\n".join(lines)),
    ])


def server_message(guild: discord.Guild) -> LayoutView:
    created = discord.utils.format_dt(guild.created_at, style="F")
    created_rel = discord.utils.format_dt(guild.created_at, style="R")
    total = guild.member_count or 0
    humans = sum(1 for member in guild.members if not member.bot) if guild.chunked else "?"
    bots = total - humans if guild.chunked else "?"
    lines = [
        f"- **Owner** {guild.owner.mention if guild.owner else 'Unknown'}",
        f"- **Created** {created} ({created_rel})",
        f"- **Members** {total:,} ({humans} humans, {bots} bots)",
        f"- **Channels** {len(guild.text_channels)} text / {len(guild.voice_channels)} voice",
        f"- **Roles** {len(guild.roles):,}",
        f"- **Boost** Level {guild.premium_tier} ({guild.premium_subscription_count or 0} boosts)",
    ]
    if guild.description:
        lines.append(f"\n> {guild.description[:200]}")
    header = TextDisplay(f"## {guild.name}\n`{guild.id}`")
    if guild.icon:
        header = Section(header, accessory=Thumbnail(guild.icon.url))
    return _view([header, Separator(spacing=SeparatorSpacing.small), TextDisplay("\n".join(lines))])


def avatar_message(user: discord.User) -> LayoutView:
    view = _view([
        Section(TextDisplay(f"## {user.display_name}\n`{user.id}`"), accessory=Thumbnail(user.display_avatar.url)),
    ])
    row = ActionRow()
    row.add_item(Button(style=ButtonStyle.link, label="Open Avatar", url=user.display_avatar.url))
    view.add_item(row)
    return view
