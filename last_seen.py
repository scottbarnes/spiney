from datetime import datetime, timezone
from typing import Final
from zoneinfo import ZoneInfo

from discord.member import Member as DiscordMember
from discord.message import Message
from discord.user import User as DiscordUser
from sqlalchemy.orm import Session

from utilities import get_or_create_user

LAST_SEEN_PREFIX: Final = ".last"


async def update_last_seen(db_session: Session, discord_user: DiscordUser | DiscordMember, message: str) -> None:
    """Set/update the last thing `discord_user` said."""
    user = get_or_create_user(db_session=db_session, name=discord_user.name, discord_id=discord_user.id)
    user.last_line = message
    user.last_seen = datetime.now(timezone.utc)


async def get_last_seen(db_session: Session, discord_user: DiscordUser | DiscordMember) -> str | None:
    """Retrieve the last thing `discord_user` said."""
    user = get_or_create_user(db_session=db_session, name=discord_user.name, discord_id=discord_user.id)
    if not user.last_seen:
        return None

    pacific_time = user.last_seen.astimezone(ZoneInfo("America/Los_Angeles"))
    formatted_time = pacific_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    return f"Last saw {discord_user} at {formatted_time} saying: {user.last_line}"


async def check_for_last_seen_info(db_session: Session, message: Message) -> str | None:
    """
    Coordination logic for the last seen functionality.

    This determines whether to look for last seen info based on the current
    message.
    """
    if not message.content.startswith(LAST_SEEN_PREFIX):
        return None

    if not message.mentions:
        return "No matching user. Use the @mention syntax."

    mentioned_user = message.mentions[0]
    if last_seen_info := await get_last_seen(db_session=db_session, discord_user=mentioned_user):
        return last_seen_info
    else:
        return "No last seen info."
