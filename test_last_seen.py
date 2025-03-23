from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from freezegun import freeze_time
from sqlalchemy import select
from sqlalchemy.orm import Session

from last_seen import get_last_seen, update_last_seen
from models import User
from test_models import db_session


@dataclass(slots=True)
class DiscordUser:
    """Small test class until I figure out what the discord.py Author object is."""

    id: int
    name: str


@freeze_time("2024-06-01 20:00:00", tz_offset=-8)
@pytest.mark.asyncio
async def test_update_last_seen(db_session: Session) -> None:
    """Ensure the last seen information updates properly."""
    test_user_1 = DiscordUser(name="Test User 1", id=1)
    test_user_2 = DiscordUser(name="Test User 2", id=2)
    test_user_1_message_1 = "I said something."
    test_user_1_message_2 = "I said another thing. 🦆"
    test_user_2_message_1 = "Here's some interjection."

    # First user says something.
    await update_last_seen(db_session=db_session, discord_user=test_user_1, message=test_user_1_message_1)
    retrieved_user = db_session.execute(select(User).where(User.name == "Test User 1")).scalar_one_or_none()
    assert retrieved_user is not None
    assert retrieved_user.last_line == test_user_1_message_1
    assert retrieved_user.last_seen == datetime(2024, 6, 1, 12, 0)

    # A second user says something.
    await update_last_seen(db_session=db_session, discord_user=test_user_2, message=test_user_2_message_1)
    retrieved_user = db_session.execute(select(User).where(User.name == "Test User 2")).scalar_one_or_none()
    assert retrieved_user is not None
    assert retrieved_user.last_line == test_user_2_message_1

    # The first user says another thing.
    await update_last_seen(db_session=db_session, discord_user=test_user_1, message=test_user_1_message_2)
    retrieved_user = db_session.execute(select(User).where(User.name == "Test User 1")).scalar_one_or_none()
    assert retrieved_user is not None
    assert retrieved_user.last_line == test_user_1_message_2


@freeze_time("2024-06-01 20:00:00", tz_offset=-8)
@pytest.mark.asyncio
async def test_get_last_seen(db_session: Session) -> None:
    """Ensure the last seen information can be retrieved."""
    test_user = DiscordUser(name="Test User 1", id=1)
    test_message = "I said another thing. 🦆"
    expected_message = (
        "Last saw DiscordUser(id=1, name='Test User 1') at 2024-06-01 12:00:00 PDT saying: I said another thing. 🦆"
    )

    db_user = User(name="Test User 1", discord_id=1)
    db_user.last_line = test_message
    db_user.last_seen = datetime.now(timezone.utc)
    db_session.add(db_user)
    db_session.commit()

    got = await get_last_seen(db_session=db_session, discord_user=test_user)
    assert got == expected_message
