import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parent.parent / "ruxy.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id    INTEGER PRIMARY KEY,
            reason     TEXT    DEFAULT '',
            created_at TEXT    DEFAULT (datetime('now')),
            expires_at TEXT,
            is_permanent BOOLEAN DEFAULT 0,
            created_by INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS spam_state (
            user_id    INTEGER PRIMARY KEY,
            spam_count INTEGER DEFAULT 0,
            offense_count INTEGER DEFAULT 0,
            last_cmd_time TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sync_state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS command_metrics (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            command   TEXT    NOT NULL,
            user_id   INTEGER NOT NULL,
            guild_id  INTEGER,
            timestamp TEXT    DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS settings (
            guild_id INTEGER NOT NULL,
            key      TEXT    NOT NULL,
            value    TEXT    NOT NULL,
            PRIMARY KEY (guild_id, key)
        );
        CREATE TABLE IF NOT EXISTS log_channels (
            channel_id INTEGER PRIMARY KEY,
            repo       TEXT NOT NULL,
            branch     TEXT NOT NULL DEFAULT 'main',
            last_sha   TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS afk_users (
            user_id  INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            reason   TEXT    DEFAULT '',
            since    TEXT    DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, guild_id)
        );
    """)
    conn.commit()
    conn.close()


def blacklist_add(user_id: int, reason: str = "", mod_id: int = 0, duration_mins: int = None) -> None:
    conn = get_conn()
    expires_at = None
    is_permanent = 0
    
    if duration_mins is None:
        is_permanent = 1
    else:
        expiry = datetime.now() + timedelta(minutes=duration_mins)
        expires_at = expiry.strftime("%Y-%m-%d %H:%M:%S")
    
    conn.execute(
        "INSERT OR REPLACE INTO blacklist (user_id, reason, created_by, expires_at, is_permanent) VALUES (?, ?, ?, ?, ?)",
        (user_id, reason, mod_id, expires_at, is_permanent),
    )
    conn.commit()
    conn.close()


def blacklist_remove(user_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def is_blacklisted(user_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute("SELECT expires_at, is_permanent FROM blacklist WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return False
    
    if row["is_permanent"]:
        return True
    
    if row["expires_at"]:
        expiry = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < expiry:
            return True
            
    return False


def track_spam(user_id: int) -> tuple[bool, int]:
    """
    Tracks command frequency. 
    Returns (is_spamming, current_offense_count).
    Threshold: 3 commands in 5 seconds.
    """
    conn = get_conn()
    now = datetime.now()
    
    row = conn.execute("SELECT spam_count, offense_count, last_cmd_time FROM spam_state WHERE user_id = ?", (user_id,)).fetchone()
    
    if row:
        spam_count = row["spam_count"]
        offense_count = row["offense_count"]
        last_time = datetime.strptime(row["last_cmd_time"], "%Y-%m-%d %H:%M:%S.%f")
    else:
        spam_count = 0
        offense_count = 0
        last_time = now - timedelta(seconds=10)
    
    diff = (now - last_time).total_seconds()
    
    if diff < 5:
        spam_count += 1
    else:
        spam_count = 1
    
    conn.execute(
        "INSERT OR REPLACE INTO spam_state (user_id, spam_count, offense_count, last_cmd_time) VALUES (?, ?, ?, ?)",
        (user_id, spam_count, offense_count, now.strftime("%Y-%m-%d %H:%M:%S.%f")),
    )
    
    if spam_count >= 3:
        offense_count += 1
        conn.execute(
            "UPDATE spam_state SET spam_count = 0, offense_count = ?, last_cmd_time = ? WHERE user_id = ?",
            (offense_count, now.strftime("%Y-%m-%d %H:%M:%S.%f"), user_id),
        )
        conn.commit()
        conn.close()
        return True, offense_count
    
    conn.commit()
    conn.close()
    return False, offense_count


def reset_spam(user_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM spam_state WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_sync_version() -> str:
    conn = get_conn()
    cur = conn.execute("SELECT value FROM sync_state WHERE key = 'synced_version'")
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else ""


def set_sync_version(version: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO sync_state (key, value) VALUES ('synced_version', ?)",
        (version,),
    )
    conn.commit()
    conn.close()


def log_command(command: str, user_id: int, guild_id: int | None) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO command_metrics (command, user_id, guild_id) VALUES (?, ?, ?)",
        (command, user_id, guild_id),
    )
    conn.commit()
    conn.close()


def get_command_stats() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM command_metrics").fetchone()["c"]
    rows = conn.execute(
        "SELECT command, COUNT(*) as count FROM command_metrics GROUP BY command ORDER by count DESC"
    ).fetchall()
    conn.close()
    return {
        "total": total,
        "commands": {r["command"]: r["count"] for r in rows},
    }


def add_log_channel(channel_id: int, repo: str, branch: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO log_channels (channel_id, repo, branch, last_sha) VALUES (?, ?, ?, ?)",
        (channel_id, repo, branch, ""),
    )
    conn.commit()
    conn.close()


def remove_log_channel(channel_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM log_channels WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()


def get_log_channels() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT channel_id, repo, branch, last_sha FROM log_channels").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_last_sha(channel_id: int, sha: str) -> None:
    conn = get_conn()
    conn.execute("UPDATE log_channels SET last_sha = ? WHERE channel_id = ?", (sha, channel_id))
    conn.commit()
    conn.close()


def set_afk(user_id: int, guild_id: int, reason: str = "") -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO afk_users (user_id, guild_id, reason, since) VALUES (?, ?, ?, datetime('now'))",
        (user_id, guild_id, reason),
    )
    conn.commit()
    conn.close()


def remove_afk(user_id: int, guild_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM afk_users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
    conn.commit()
    conn.close()


def get_afk(user_id: int, guild_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT reason, since FROM afk_users WHERE user_id = ? AND guild_id = ?",
        (user_id, guild_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None
