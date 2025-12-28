from dataclasses import dataclass

from discord.member import Member
from sqlalchemy.orm import Session


@dataclass(slots=True)
class DiscordUser:
    """
    Small test class until I figure out what the discord.py Author object is.

    This should be refactored and imported from one place rather than
    copy/pasted. It should also probably be done correctly using the actual
    object.
    """

    id: int
    name: str


async def add_quote_to_db(db_session: Session, member: Member | DiscordUser, channel: str, quote: str) -> None:
    """
    Takes a Discord member, channel, and quote, creates a Quote object and adds
    it to the database.
    """
    # This should execute the logic to add a quote to the database. If the test
    # for this function passes, that should mean the basic logic is functioning.
    # See `url_history.add_quote_to_db` for a reference.
    pass
