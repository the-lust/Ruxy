import discord
from database.db import is_blacklisted as db_is_blacklisted, track_spam, blacklist_add
from config import JAIL_ROLE_ID


def is_jailed(member: discord.Member) -> bool:
    if not isinstance(member, discord.Member) or member.guild is None:
        return False
    return member.get_role(JAIL_ROLE_ID) is not None


def can_use_bot(member: discord.Member) -> tuple[bool, str]:
    # 1. Check permanent/temp blacklist
    if db_is_blacklisted(member.id):
        return False, "You are blacklisted from using this bot."
    
    # 2. Check jail
    if is_jailed(member):
        return False, "You are in jail and cannot use this bot."
    
    # 3. Anti-spam check
    is_spamming, offense_count = track_spam(member.id)
    if is_spamming:
        if offense_count >= 3:
            # Permanent ban for 3+ offenses
            blacklist_add(member.id, reason="Repeated spamming (3+ offenses)", duration_mins=None)
            return False, "You have been permanently blacklisted for repeated spamming."
        
        # Temporary ban based on offense count
        duration = 10 if offense_count == 1 else 60
        blacklist_add(member.id, reason=f"Spamming (Offense {offense_count})", duration_mins=duration)
        return False, f"You are temporarily blacklisted for {duration} minutes due to spamming."
        
    return True, ""
