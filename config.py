import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent

load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")

BOT_COLOR = 0xA259FF
BOT_NAME = "Ruxy"
BOT_VERSION = "4.3.0"
BOT_DESCRIPTION = "Developer companion for the Rux programming language"

LOG_DIR = BASE_DIR / "logs"

OWNERS: set[int] = set()
_raw = os.getenv("OWNER_IDS", "")
if _raw:
    for part in _raw.split(","):
        part = part.strip()
        if part:
            try:
                OWNERS.add(int(part))
            except ValueError:
                pass

JAIL_ROLE_ID = 1510089784205381702
MOD_ROLE_ID = 1509981231775748196
ADMIN_ROLE_ID = 1509989094132940880

REPOS: dict[str, str] = {
    "rux":       "https://github.com/rux-lang/Rux",
    "std":       "https://github.com/rux-lang/Std",
    "windows":   "https://github.com/rux-lang/Windows",
    "linux":     "https://github.com/rux-lang/Linux",
    "bsd":       "https://github.com/rux-lang/BSD",
    "macos":     "https://github.com/rux-lang/MacOS",
    "bot":       "https://github.com/rux-lang/Ruxy",
    "website":   "https://github.com/rux-lang/Web",
    "illumos":   "https://github.com/rux-lang/Illumos",
    "tests":     "https://github.com/rux-lang/Tests",
    "tutorials": "https://github.com/rux-lang/Tutorials",
    "zed":       "https://github.com/rux-lang/Zed",
    "vscode":    "https://github.com/rux-lang/VSCode",
    "sublime":   "https://github.com/rux-lang/SublimeText",
}

REPO_ALIASES: dict[str, str] = {
    "vsc":           "vscode",
    "sublimetext":   "sublime",
}

GITHUB_ORG = "rux-lang"
GITHUB_TIMEOUT = 10
CACHE_TTL = 120

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_TIMEOUT = 30
AI_MAX_TOKENS = 1024
