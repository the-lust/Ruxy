import logging

import discord
from discord import app_commands, ButtonStyle
from discord.ext import commands
from discord.ui import (
    LayoutView, Container, TextDisplay, Section,
    Thumbnail, Separator, ActionRow, Button, Select,
)
from discord.enums import SeparatorSpacing

from config import REPOS, REPO_ALIASES, GITHUB_ORG
from database.db import log_command
from services import cv2, github_api
from datetime import datetime, timezone
from utils.checks import can_use_bot

logger = logging.getLogger(__name__)


def _ts(iso: str, style: str = "R") -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return f"<t:{int(dt.timestamp())}:{style}>"
    except (ValueError, AttributeError):
        return iso


REPO_CHOICES: list[app_commands.Choice[str]] = [
    app_commands.Choice(name="  Rux (Compiler)", value="rux"),
    app_commands.Choice(name="  Standard Library", value="std"),
    app_commands.Choice(name="  Windows Library", value="windows"),
    app_commands.Choice(name="  Linux Library", value="linux"),
    app_commands.Choice(name="  BSD Library", value="bsd"),
    app_commands.Choice(name="  MacOS Library", value="macos"),
    app_commands.Choice(name="  Illumos Library", value="illumos"),
    app_commands.Choice(name="  Ruxy Bot", value="bot"),
    app_commands.Choice(name="  Rux Website", value="website"),
    app_commands.Choice(name="  Rux Tests", value="tests"),
    app_commands.Choice(name="  Tutorials", value="tutorials"),
    app_commands.Choice(name="  Zed Extension", value="zed"),
    app_commands.Choice(name="  VS Code Extension", value="vscode"),
    app_commands.Choice(name="  Sublime Text Extension", value="sublime"),
]


def _resolve_repo(key: str) -> tuple[str, str]:
    actual = REPO_ALIASES.get(key, key)
    url = REPOS.get(actual)
    if url:
        return actual, url
    return key, ""


async def _repo_ac(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not current:
        return REPO_CHOICES[:12]
    lower = current.lower()
    return [c for c in REPO_CHOICES if lower in c.value.lower() or lower in c.name.lower()]


# ── Repo view with branch selector ───────────────────────────────────────────

class RepoView(LayoutView):
    """
    LayoutView for /repo. Contains:
      • Container with all repo info + accent border
      • Separate ActionRow with link buttons
      • Separate ActionRow with branch Select (when >1 branch)
    The Select lives in its own ActionRow — never mixed with link Buttons.
    """

    def __init__(
        self,
        name: str,
        data: dict,
        branch: str,
        branches: list[str],
        url: str,
    ):
        super().__init__(timeout=180)
        self._name = name
        self._data = data
        self._branch = branch
        self._branches = branches
        self._url = url
        self._build()

    def _build(self) -> None:
        self.clear_items()
        data = self._data
        name = self._name
        branch = self._branch
        branches = self._branches
        url = self._url

        desc = (data.get("description") or "")[:250]
        lang = data.get("language") or ""
        stars = data.get("stargazers_count") or 0
        forks = data.get("forks_count") or 0
        issues = data.get("open_issues_count") or 0
        license_spdx = (data.get("license") or {}).get("spdx_id") or ""
        topics = (data.get("topics") or [])[:6]
        pushed = data.get("pushed_at", "")
        created = data.get("created_at", "")
        size = data.get("size", 0)
        avatar = (data.get("owner") or {}).get("avatar_url") or ""

        # Build content text
        parts: list[str] = [f"## **{name}**"]
        if desc:
            parts.append(desc)
        badges = []
        if lang:
            badges.append(f"`{lang}`")
        if license_spdx:
            badges.append(f"`{license_spdx}`")
        if badges:
            parts.append(" ".join(badges))
        if topics:
            parts.append(" ".join(f"`{t}`" for t in topics))
        parts.append("\n**Repository Info**")
        stats = []
        if stars:
            stats.append(f"★ **{stars:,}** stars")
        if forks:
            stats.append(f"⑂ **{forks:,}** forks")
        if issues:
            stats.append(f"！**{issues}** issues")
        if stats:
            parts.append(" · ".join(stats))
        if created:
            parts.append(f"• **Created** {_ts(created, 'F')} ({_ts(created, 'R')})")
        if pushed:
            parts.append(f"• **Last Push** {_ts(pushed, 'R')}")
        bc = f"`{branch}`"
        if branches and len(branches) > 1:
            bc += f" ({len(branches)} branches)"
        parts.append(f"• **Branch** {bc}")
        if size:
            size_mb = size / 1024
            val = f"{size_mb:.1f} MB" if size_mb > 1 else f"{size} KB"
            parts.append(f"• **Size** {val}")

        # Container with accent border (the "background")
        container_items: list = [TextDisplay("\n".join(parts))]
        if avatar:
            container_items.insert(0, Section(
                TextDisplay(f"**rux-lang/{name}**"),
                accessory=Thumbnail(avatar),
            ))
            container_items.insert(1, Separator(spacing=SeparatorSpacing.small))

        self.add_item(Container(*container_items, accent_color=0xA259FF))

        # Link button row (standalone ActionRow — no selects here)
        btn_row = ActionRow()
        btn_row.add_item(Button(style=ButtonStyle.link, label="  Open Repository", url=url))
        btn_row.add_item(Button(style=ButtonStyle.link, label="  GitHub Org", url=f"https://github.com/{GITHUB_ORG}"))
        self.add_item(btn_row)

        # Branch selector in its own separate ActionRow
        if len(branches) > 1:
            options = [
                discord.SelectOption(label=b[:100], value=b, default=(b == branch))
                for b in branches[:25]
            ]
            sel = Select(
                placeholder=f"  Branch: {branch}",
                min_values=1,
                max_values=1,
                options=options,
            )

            async def _on_branch(interaction: discord.Interaction) -> None:
                selected = sel.values[0]
                fresh = await github_api.get_repo(self._name) or self._data
                self._data = fresh
                self._branch = selected
                self._url = fresh.get("html_url", self._url)
                self._build()
                await interaction.response.edit_message(view=self)

            sel.callback = _on_branch
            sel_row = ActionRow()
            sel_row.add_item(sel)
            self.add_item(sel_row)


# ── Contributors paginated view ───────────────────────────────────────────────

class ContributorView(LayoutView):
    """
    Paginated contributor list. Each contributor shows as a compact Section
    with a small Thumbnail (avatar) and inline text. Pages of 8.
    """

    PER_PAGE = 8

    def __init__(self, name: str, data: list[dict], info: dict):
        super().__init__(timeout=180)
        self._name = name
        self._data = data
        self._info = info
        self._page = 0
        self._total_pages = max(1, (len(data) + self.PER_PAGE - 1) // self.PER_PAGE)
        self._rebuild()

    def _chunk(self) -> list[dict]:
        s = self._page * self.PER_PAGE
        return self._data[s : s + self.PER_PAGE]

    def _rebuild(self) -> None:
        self.clear_items()
        chunk = self._chunk()
        base = self._page * self.PER_PAGE

        items: list = [
            TextDisplay(
                f"## Contributors — {self._name}\n"
                f"-# Page {self._page + 1}/{self._total_pages}  ·  {len(self._data)} total"
            ),
            Separator(spacing=SeparatorSpacing.small),
        ]

        for i, c in enumerate(chunk):
            idx = base + i + 1
            total = c.get("total_commits", c.get("contributions", 0))
            login = c.get("login", "unknown")
            avatar = c.get("avatar_url", "")
            profile_url = c.get("html_url", f"https://github.com/{login}")

            # All branches this contributor has commits on
            branches = c.get("branches", {})
            branch_str = ""
            if branches:
                sorted_b = sorted(branches.items(), key=lambda x: -x[1])
                branch_str = "  " + "  ".join(f"`{b}`" for b, _ in sorted_b[:4])

            text = f"**{idx}.** [`{login}`]({profile_url})  —  **{total}** commits{branch_str}"

            # Section gives a small thumbnail on the right; Section is compact
            if avatar:
                items.append(Section(TextDisplay(text), accessory=Thumbnail(avatar)))
            else:
                items.append(TextDisplay(text))

        self.add_item(Container(*items, accent_color=0xA259FF))

        # Navigation + GitHub link
        row = ActionRow()
        if self._page > 0:
            prev_btn = Button(style=ButtonStyle.secondary, label="◀  Prev")
            prev_btn.callback = self._prev
            row.add_item(prev_btn)
        row.add_item(Button(
            style=ButtonStyle.link,
            label="  View on GitHub",
            url=self._info.get("html_url", f"https://github.com/{GITHUB_ORG}/{self._name}"),
        ))
        if self._page < self._total_pages - 1:
            next_btn = Button(style=ButtonStyle.secondary, label="Next  ▶")
            next_btn.callback = self._next
            row.add_item(next_btn)
        self.add_item(row)

    async def _prev(self, interaction: discord.Interaction) -> None:
        self._page -= 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _next(self, interaction: discord.Interaction) -> None:
        self._page += 1
        self._rebuild()
        await interaction.response.edit_message(view=self)


# ── Other GitHub data views ───────────────────────────────────────────────────

def _release_view(name: str, releases: list, info: dict) -> LayoutView:
    lines: list[str] = []
    accent = 0x57F287
    for r in releases[:5]:
        tag = r.get("tag_name", "")
        rname = r.get("name") or tag
        url = r.get("html_url", "")
        prerelease = r.get("prerelease", False)
        published = r.get("published_at", "")
        body = (r.get("body") or "")[:200]
        lines.append(f"### [{rname}]({url})")
        if published:
            lines.append(f"`{tag}`  ·  {_ts(published, 'R')}")
        if prerelease:
            lines.append("*Pre-release*")
            accent = 0xFEE75C
        if body:
            lines.append(f"> {body.replace(chr(10), ' ').strip()}")
        lines.append("")

    avatar = (info.get("owner") or {}).get("avatar_url", "")
    items: list = []
    if avatar:
        items.append(Section(
            TextDisplay(f"**rux-lang/{name}**"),
            accessory=Thumbnail(avatar),
        ))
        items.append(Separator(spacing=SeparatorSpacing.small))
    items.append(TextDisplay(f"## Recent Releases — {name}\n\n" + "\n".join(lines)))

    view = LayoutView(timeout=180)
    view.add_item(Container(*items, accent_color=accent))
    row = ActionRow()
    row.add_item(Button(
        style=ButtonStyle.link,
        label="  All Releases",
        url=f"https://github.com/{GITHUB_ORG}/{name}/releases",
    ))
    view.add_item(row)
    return view


def _issues_view(name: str, issues: list, state: str, info: dict) -> LayoutView:
    lines: list[str] = []
    accent = 0xED4245 if state == "open" else 0x57F287
    for i in issues[:5]:
        num = i.get("number", 0)
        title = (i.get("title") or "")[:200]
        url = i.get("html_url", "")
        labels = (i.get("labels") or [])[:3]
        created = i.get("created_at", "")
        user = (i.get("user") or {}).get("login", "unknown")
        lines.append(f"### [#{num} {title}]({url})")
        if labels:
            lines.append(" ".join(f"`{l['name']}`" for l in labels))
        lines.append(f"by **{user}**  ·  {_ts(created, 'R')}")
        lines.append("")

    avatar = (info.get("owner") or {}).get("avatar_url", "")
    items: list = []
    if avatar:
        items.append(Section(
            TextDisplay(f"**rux-lang/{name}**"),
            accessory=Thumbnail(avatar),
        ))
        items.append(Separator(spacing=SeparatorSpacing.small))
    items.append(TextDisplay(f"## {state.title()} Issues — {name}\n\n" + "\n".join(lines)))

    view = LayoutView(timeout=180)
    view.add_item(Container(*items, accent_color=accent))
    row = ActionRow()
    row.add_item(Button(
        style=ButtonStyle.link,
        label=f"  {state.title()} Issues",
        url=f"https://github.com/{GITHUB_ORG}/{name}/issues?q=is%3Aissue+is%3A{state}",
    ))
    view.add_item(row)
    return view


def _pulls_view(name: str, pulls: list, state: str, info: dict) -> LayoutView:
    lines: list[str] = []
    accent = 0x57F287
    for pr in pulls[:5]:
        num = pr.get("number", 0)
        title = (pr.get("title") or "")[:200]
        url = pr.get("html_url", "")
        merged = pr.get("merged_at")
        pr_state = pr.get("state", "open")
        created = pr.get("created_at", "")
        user = (pr.get("user") or {}).get("login", "unknown")
        if merged:
            accent = 0xA259FF
        elif pr_state == "closed":
            accent = 0xED4245
        status = "Merged" if merged else ("Closed" if pr_state == "closed" else "Open")
        lines.append(f"### [#{num} {title}]({url})")
        lines.append(f"`{status}`  by **{user}**  ·  {_ts(created, 'R')}")
        lines.append("")

    avatar = (info.get("owner") or {}).get("avatar_url", "")
    items: list = []
    if avatar:
        items.append(Section(
            TextDisplay(f"**rux-lang/{name}**"),
            accessory=Thumbnail(avatar),
        ))
        items.append(Separator(spacing=SeparatorSpacing.small))
    items.append(TextDisplay(f"## {state.title()} PRs — {name}\n\n" + "\n".join(lines)))

    view = LayoutView(timeout=180)
    view.add_item(Container(*items, accent_color=accent))
    row = ActionRow()
    row.add_item(Button(
        style=ButtonStyle.link,
        label=f"  {state.title()} PRs",
        url=f"https://github.com/{GITHUB_ORG}/{name}/pulls?q=is%3Apr+is%3A{state}",
    ))
    view.add_item(row)
    return view


def _packages_view() -> LayoutView:
    lines = "\n".join(
        f"• `{k}`  —  [{v.split('/')[-1]}]({v})" for k, v in sorted(REPOS.items())
    )
    return cv2.build(
        "## 📦  Rux Ecosystem",
        "> Core repositories in the Rux programming language ecosystem.",
        f"### Available Packages\n{lines}",
    )


# ── Cog ───────────────────────────────────────────────────────────────────────

class GithubCog(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    @app_commands.command(name="repo", description="Get information about a Rux repository")
    @app_commands.autocomplete(repository=_repo_ac)
    @app_commands.describe(repository="Repository name", branch="Branch name (default: main)")
    @app_commands.checks.cooldown(3, 30)
    async def repo(
        self,
        interaction: discord.Interaction,
        repository: str,
        branch: str = "main",
    ) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return

        log_command("repo", interaction.user.id, interaction.guild_id)
        name, url = _resolve_repo(repository)

        if not url:
            await interaction.response.defer()
            exists = await github_api.repo_exists(repository)
            if not exists:
                await interaction.followup.send(
                    view=cv2.error_message(f"Repository `{repository}` not found under `{GITHUB_ORG}`."),
                    ephemeral=True,
                )
                return
            url = f"https://github.com/{GITHUB_ORG}/{repository}"
            name = repository

        info = await github_api.get_repo(name) or {}

        if branch != info.get("default_branch", "main"):
            branch_ok = await github_api.branch_exists(name, branch)
            if not branch_ok:
                await interaction.response.send_message(
                    view=cv2.error_message(f"Repository `{name}` has no branch `{branch}`."),
                    ephemeral=True,
                )
                return

        branches = await github_api.get_branch_names(name)
        view = RepoView(name, info, branch, branches, info.get("html_url", url))

        if interaction.response.is_done():
            await interaction.followup.send(view=view)
        else:
            await interaction.response.send_message(view=view)

    @app_commands.command(name="contributors", description="Top contributors of a Rux repository")
    @app_commands.autocomplete(repository=_repo_ac)
    @app_commands.checks.cooldown(3, 30)
    async def contributors(
        self,
        interaction: discord.Interaction,
        repository: str,
    ) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return

        log_command("contributors", interaction.user.id, interaction.guild_id)
        name, _ = _resolve_repo(repository)
        info = await github_api.get_repo(name)
        if not info:
            await interaction.response.send_message(
                view=cv2.error_message(f"Repository `{name}` not found."), ephemeral=True
            )
            return

        await interaction.response.defer()
        data = await github_api.get_contributors_with_branches(name)
        if not data:
            await interaction.followup.send(view=cv2.info_message(f"  {name}", "No contributors found."))
            return

        await interaction.followup.send(view=ContributorView(name, data, info))

    @app_commands.command(name="releases", description="Recent releases of a Rux repository")
    @app_commands.autocomplete(repository=_repo_ac)
    @app_commands.checks.cooldown(3, 30)
    async def releases(
        self,
        interaction: discord.Interaction,
        repository: str,
    ) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return

        log_command("releases", interaction.user.id, interaction.guild_id)
        name, _ = _resolve_repo(repository)
        info = await github_api.get_repo(name)
        if not info:
            await interaction.response.send_message(
                view=cv2.error_message(f"Repository `{name}` not found."), ephemeral=True
            )
            return

        await interaction.response.defer()
        data = await github_api.get_releases(name)
        if not data:
            await interaction.followup.send(view=cv2.info_message(f"  {name}", "No releases found."))
            return

        await interaction.followup.send(view=_release_view(name, data, info))

    @app_commands.command(name="issues", description="Recent open issues for a Rux repository")
    @app_commands.autocomplete(repository=_repo_ac)
    @app_commands.describe(state="Issue state: open (default) or closed")
    @app_commands.checks.cooldown(2, 30)
    async def issues(
        self,
        interaction: discord.Interaction,
        repository: str,
        state: str = "open",
    ) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return

        log_command("issues", interaction.user.id, interaction.guild_id)
        name, _ = _resolve_repo(repository)
        info = await github_api.get_repo(name)
        if not info:
            await interaction.response.send_message(
                view=cv2.error_message(f"Repository `{name}` not found."), ephemeral=True
            )
            return

        await interaction.response.defer()
        data = await github_api.get_issues(name, state=state)
        if not data:
            await interaction.followup.send(view=cv2.info_message(f"  {name}", f"No **{state}** issues found."))
            return

        await interaction.followup.send(view=_issues_view(name, data, state, info))

    @app_commands.command(name="pulls", description="Recent pull requests for a Rux repository")
    @app_commands.autocomplete(repository=_repo_ac)
    @app_commands.describe(state="PR state: open (default), closed, or all")
    @app_commands.checks.cooldown(2, 30)
    async def pulls(
        self,
        interaction: discord.Interaction,
        repository: str,
        state: str = "open",
    ) -> None:
        ok, msg = can_use_bot(interaction.user)
        if not ok:
            await interaction.response.send_message(view=cv2.error_message(msg), ephemeral=True)
            return

        log_command("pulls", interaction.user.id, interaction.guild_id)
        name, _ = _resolve_repo(repository)
        info = await github_api.get_repo(name)
        if not info:
            await interaction.response.send_message(
                view=cv2.error_message(f"Repository `{name}` not found."), ephemeral=True
            )
            return

        await interaction.response.defer()
        data = await github_api.get_pulls(name, state=state)
        if not data:
            await interaction.followup.send(view=cv2.info_message(f"  {name}", f"No **{state}** pull requests found."))
            return

        await interaction.followup.send(view=_pulls_view(name, data, state, info))

    @app_commands.command(name="docs", description="Link to Rux documentation")
    @app_commands.checks.cooldown(5, 10)
    async def docs(self, interaction: discord.Interaction) -> None:
        view = cv2.build(
            "## 📖  Rux Documentation\n> Explore the official Rux language documentation, guides, and references.",
        )
        row = ActionRow()
        row.add_item(Button(style=ButtonStyle.link, label="  Documentation", url="https://rux-lang.org/docs"))
        row.add_item(Button(style=ButtonStyle.link, label="  GitHub", url="https://github.com/rux-lang"))
        row.add_item(Button(style=ButtonStyle.link, label="  Language Home", url="https://rux-lang.org"))
        view.add_item(row)
        await interaction.response.send_message(view=view)

    @app_commands.command(name="packages", description="Rux ecosystem packages")
    @app_commands.checks.cooldown(3, 20)
    async def packages(self, interaction: discord.Interaction) -> None:
        view = _packages_view()
        row = ActionRow()
        row.add_item(Button(style=ButtonStyle.link, label="  GitHub Org", url=f"https://github.com/{GITHUB_ORG}"))
        view.add_item(row)
        await interaction.response.send_message(view=view)

    @repo.error
    @contributors.error
    @releases.error
    @issues.error
    @pulls.error
    async def github_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    view=cv2.warning_message(f"Slow down! Try again in `{error.retry_after:.1f}s`."),
                    ephemeral=True,
                )


async def setup(client: discord.Client) -> None:
    await client.add_cog(GithubCog(client))
