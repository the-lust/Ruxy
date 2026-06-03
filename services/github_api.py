import aiohttp
import logging
from typing import Any

from config import GITHUB_ORG, GITHUB_TIMEOUT
from services.cache import github_cache

logger = logging.getLogger("github")

GITHUB_API = "https://api.github.com"
HEADERS = {
    "User-Agent": "Ruxy-Bot/4.0",
    "Accept": "application/vnd.github.v3+json",
}


async def _fetch(url: str) -> dict | list | None:
    cached = github_cache.get(url)
    if cached is not None:
        return cached

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=GITHUB_TIMEOUT)
            ) as resp:
                if resp.status != 200:
                    logger.warning("GitHub %s returned %d", url, resp.status)
                    return None
                data = await resp.json()
                github_cache.set(url, data)
                return data
        except Exception as e:
            logger.error("GitHub request failed: %s - %s", url, e)
            return None


async def repo_exists(name: str) -> bool:
    return await _fetch(f"{GITHUB_API}/repos/{GITHUB_ORG}/{name}") is not None


async def get_repo(name: str) -> dict | None:
    return await _fetch(f"{GITHUB_API}/repos/{GITHUB_ORG}/{name}")


async def branch_exists(repo: str, branch: str) -> bool:
    return (
        await _fetch(f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo}/branches/{branch}")
        is not None
    )


async def get_contributors(repo: str) -> list[dict[str, Any]]:
    all_data: list[dict[str, Any]] = []
    page = 1
    while True:
        data = await _fetch(
            f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo}/contributors?per_page=100&page={page}"
        )
        if not isinstance(data, list) or not data:
            break
        all_data.extend(data)
        if len(data) < 100:
            break
        page += 1
    return all_data


async def get_releases(repo: str, limit: int = 5) -> list[dict[str, Any]]:
    data = await _fetch(
        f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo}/releases?per_page={limit}"
    )
    return data if isinstance(data, list) else []


async def get_issues(
    repo: str, state: str = "open", limit: int = 5
) -> list[dict[str, Any]]:
    data = await _fetch(
        f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo}/issues?state={state}&per_page={limit}&sort=created&direction=desc"
    )
    return data if isinstance(data, list) else []


async def get_pulls(repo: str, state: str = "open", limit: int = 5) -> list[dict[str, Any]]:
    data = await _fetch(
        f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo}/pulls?state={state}&per_page={limit}&sort=created&direction=desc"
    )
    return data if isinstance(data, list) else []


async def get_commits(repo: str, branch: str = "main", limit: int = 3) -> list[dict[str, Any]]:
    data = await _fetch(
        f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo}/commits?sha={branch}&per_page={limit}"
    )
    return data if isinstance(data, list) else []


async def get_commit_detail(commit_url: str) -> dict | None:
    return await _fetch(commit_url)


async def get_branches(repo: str) -> list[dict[str, Any]]:
    data = await _fetch(
        f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo}/branches?per_page=30"
    )
    return data if isinstance(data, list) else []


async def get_branch_names(repo: str) -> list[str]:
    branches = await get_branches(repo)
    return [b["name"] for b in branches if isinstance(b, dict)]


async def get_contributors_with_branches(repo: str) -> list[dict[str, Any]]:
    """Fetch contributors with per-branch commit breakdown.

    Returns list of dicts:
      {login, avatar_url, html_url, total_commits, branches: {branch_name: count}}
    Sorted by total_commits descending.
    """
    branches = await get_branch_names(repo)
    authors: dict[str, dict] = {}

    for branch in branches[:10]:  # limit to 10 branches to avoid rate limits
        page = 1
        while True:
            data = await _fetch(
                f"{GITHUB_API}/repos/{GITHUB_ORG}/{repo}/commits?sha={branch}&per_page=100&page={page}"
            )
            if not isinstance(data, list) or not data:
                break
            for c in data:
                a = c.get("author")
                if not a or not isinstance(a, dict):
                    continue
                login = a.get("login")
                if not login:
                    continue
                if login not in authors:
                    authors[login] = {
                        "login": login,
                        "avatar_url": a.get("avatar_url", ""),
                        "html_url": a.get("html_url", f"https://github.com/{login}"),
                        "total_commits": 0,
                        "branches": {},
                    }
                authors[login]["total_commits"] += 1
                authors[login]["branches"][branch] = authors[login]["branches"].get(branch, 0) + 1
            if len(data) < 100:
                break
            page += 1

    result = sorted(authors.values(), key=lambda x: -x["total_commits"])
    return result
