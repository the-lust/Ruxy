import json
import logging
from datetime import datetime, timezone

import discord
from discord.ui import LayoutView, Container, TextDisplay, ActionRow, Button
from discord import ButtonStyle

from config import GITHUB_ORG

logger = logging.getLogger("github")


def _ts(iso: str, style: str = "R") -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return f"<t:{int(dt.timestamp())}:{style}>"
    except (ValueError, AttributeError):
        return iso


def build_commit_embed(
    repo: str,
    branch: str,
    commit: dict,
) -> LayoutView:
    c = commit["commit"]
    author = c["author"]
    stats = commit.get("stats", {})
    files = commit.get("files", [])
    sha_short = commit["sha"][:7]
    sha_full = commit["sha"]
    additions = stats.get("additions", 0)
    deletions = stats.get("deletions", 0)
    total_changes = stats.get("total", 0)
    message = c.get("message", "No message").split("\n")[0][:200]

    diff_lines = []
    for f in files[:10]:
        status = f.get("status", "modified")
        if status == "added":
            diff_lines.append(f"+  {f['filename']}")
        elif status == "removed":
            diff_lines.append(f"-  {f['filename']}")
        else:
            diff_lines.append(f"~  {f['filename']}")
    if len(files) > 10:
        diff_lines.append(f"*...and {len(files) - 10} more files*")

    raw = {
        "repo": repo,
        "branch": branch,
        "sha": sha_full,
        "author": author.get("name", "unknown"),
        "message": message,
        "stats": {"additions": additions, "deletions": deletions, "total": total_changes},
        "files": [f["filename"] for f in files[:5]],
    }

    color = 0xA259FF
    if additions > deletions:
        color = 0x57F287
    elif deletions > additions:
        color = 0xED4245

    now_ts = discord.utils.format_dt(datetime.now(timezone.utc), style="R")
    items = [
        TextDisplay(f"## New Commit — `{repo}/{branch}`\n> {message}"),
        TextDisplay(f"**{sha_short}** by **{author.get('name', 'unknown')}**  ·  {_ts(author.get('date', ''), 'F')} ({_ts(author.get('date', ''), 'R')})\n\n**Stats**: `+{additions}`  `-{deletions}`  `~{total_changes}` total"),
    ]
    if diff_lines:
        items.append(TextDisplay("**Files Changed**\n```diff\n" + "\n".join(diff_lines) + "\n```"))
    items.append(TextDisplay(f"**Raw**\n```json\n{json.dumps(raw, indent=2)}\n```"))
    items.append(TextDisplay(f"__Ruxy v4.0  ·  {repo}/{branch}  ·  {now_ts}__"))

    view = LayoutView(timeout=180)
    view.add_item(Container(*items, accent_color=color))
    row = ActionRow()
    row.add_item(Button(style=ButtonStyle.link, label="  View Commit", url=commit.get("html_url", "")))
    view.add_item(row)
    return view


def build_pr_embed(repo: str, pr: dict) -> LayoutView:
    title = pr.get("title", "No title")[:200]
    body = (pr.get("body") or "")[:300]
    state = pr.get("state", "open")
    merged = pr.get("merged_at")
    author = (pr.get("user") or {}).get("login", "unknown")
    author_url = (pr.get("user") or {}).get("html_url", "")
    created = pr.get("created_at", "")
    labels = (pr.get("labels") or [])[:5]
    pr_num = pr.get("number", 0)

    color = 0xA259FF if merged else (0xED4245 if state == "closed" else 0x57F287)

    raw = {
        "repo": repo,
        "pr": pr_num,
        "title": title,
        "state": "merged" if merged else state,
        "author": author,
        "labels": [l["name"] for l in labels],
    }

    items = [TextDisplay(f"## Pull Request `#{pr_num}` — {repo}\n> {title}")]
    lines = [f"**Status**: {'Merged' if merged else 'Closed' if state == 'closed' else 'Open'}"]
    lines.append(f"**Author**: [{author}]({author_url})")
    if created:
        lines.append(f"**Created**: {_ts(created, 'F')} ({_ts(created, 'R')})")
    if labels:
        lines.append("".join(f"`{l['name']}`" for l in labels))
    if body:
        lines.append(f"\n**Description**:\n{body}")
    items.append(TextDisplay("\n".join(lines)))
    items.append(TextDisplay(f"**Raw**\n```json\n{json.dumps(raw, indent=2)}\n```"))

    now_ts = discord.utils.format_dt(datetime.now(timezone.utc), style="R")
    items.append(TextDisplay(f"__Ruxy v4.0  ·  {repo}  ·  {now_ts}__"))

    view = LayoutView(timeout=180)
    view.add_item(Container(*items, accent_color=color))
    row = ActionRow()
    row.add_item(Button(style=ButtonStyle.link, label=f"  View PR #{pr_num}", url=pr.get("html_url", "")))
    view.add_item(row)
    return view
