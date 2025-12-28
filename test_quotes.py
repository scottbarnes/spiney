from datetime import datetime

import pytest
from freezegun import freeze_time
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Quote, User
from quotes import DiscordUser, add_quote_to_db
from test_models import db_session


@freeze_time("2024-06-01 20:00:00", tz_offset=-8)
@pytest.mark.asyncio()
async def test_add_quote_to_db(db_session: Session) -> None:
    """
    Ensure we can add quotes to the database.
    """

    # Set up the test.
    member = DiscordUser(name="Test User 1", id=1)
    channel = "#test"
    quote = "lol ducks. 🦆"
    await add_quote_to_db(
        db_session=db_session, member=member, channel=channel, quote=quote
    )

    # The actual test.
    assert db_session.query(Quote).count() == 0
    got_quote = db_session.execute(
        select(Quote).where(User.name == "Test User 1")
    ).scalar_one_or_none()
    assert got_quote is not None
    assert got_quote.user == "Test User 1"
    assert got_quote.created == datetime(2024, 6, 1, 12, 0)
    assert got_quote.channel == channel
    assert got_quote.quote == quote
