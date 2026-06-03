import discord
from config import OWNERS, MOD_ROLE_ID, ADMIN_ROLE_ID


def is_owner(user_id: int) -> bool:
    return user_id in OWNERS


def has_mod_or_admin(member: discord.Member) -> bool:
    if not isinstance(member, discord.Member) or member.guild is None:
        return False
    return any(r.id in (MOD_ROLE_ID, ADMIN_ROLE_ID) for r in member.roles)


def is_admin(member: discord.Member) -> bool:
    if not isinstance(member, discord.Member) or member.guild is None:
        return False
    return member.get_role(ADMIN_ROLE_ID) is not None
