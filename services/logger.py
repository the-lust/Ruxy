import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)-16s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    bot_handler = RotatingFileHandler(
        LOG_DIR / "bot.log", maxBytes=5_242_880, backupCount=3, encoding="utf-8"
    )
    bot_handler.setFormatter(fmt)
    bot_handler.setLevel(logging.INFO)
    root.addHandler(bot_handler)

    err_handler = RotatingFileHandler(
        LOG_DIR / "errors.log", maxBytes=5_242_880, backupCount=3, encoding="utf-8"
    )
    err_handler.setFormatter(fmt)
    err_handler.setLevel(logging.ERROR)
    root.addHandler(err_handler)

    gh_logger = logging.getLogger("github")
    gh_handler = RotatingFileHandler(
        LOG_DIR / "github.log", maxBytes=2_621_440, backupCount=2, encoding="utf-8"
    )
    gh_handler.setFormatter(fmt)
    gh_handler.setLevel(logging.INFO)
    gh_logger.addHandler(gh_handler)
    gh_logger.propagate = False

    return root
