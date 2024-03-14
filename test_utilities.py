from sqlalchemy.orm import Session

from models import User
from test_models import db_session
from utilities import chunk_string, get_or_create_user, get_unique_filename, get_user

import pytest


def test_get_or_create_user(db_session: Session) -> None:
    # Add an existing user
    user = User(name="Test User", discord_id=123)
    db_session.add(user)
    db_session.commit()

    # Retrieve the existing user.
    existing_user = get_or_create_user(db_session=db_session, name="Test User", discord_id=123)
    assert existing_user.discord_id == 123

    # Add a new user solely by name.
    new_user = get_or_create_user(db_session=db_session, name="New User By Name")
    assert new_user.id == 2
    assert new_user.name == "New User By Name"

    # Add a Discord user.
    new_user = get_or_create_user(db_session=db_session, name="Discord User", discord_id=456)
    assert new_user.id == 3
    assert new_user.name == "Discord User"
    assert new_user.discord_id == 456


def test_get_user(db_session: Session) -> None:
    # Add an existing user
    user = User(name="Test User", discord_id=123)
    db_session.add(user)
    db_session.commit()

    # Retrieve the existing user.
    existing_user = get_user(db_session=db_session, name="Test User", discord_id=123)
    assert existing_user.discord_id == 123
    non_existing_user = get_user(db_session=db_session, name="Not a user", discord_id=999)
    assert non_existing_user is None


@pytest.mark.asyncio()
async def test_get_unique_filename() -> None:
    """Basic test to ensure get_unique_filename() isn't obviously broken."""
    filename = "file.txt"
    got_one = await get_unique_filename(filename)
    got_two = await get_unique_filename(filename)
    got_three = await get_unique_filename(filename)
    assert got_one != got_two
    assert got_two != got_three
    assert got_one != got_three


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ["string", "length", "expected"],
    [
        ("a", 5, ["a"]),
        ("a", 1, ["a"]),
        ("a" * 3, 2, ["aa", "a"]),
        ("a" * 6, 2, ["aa", "aa", "aa"]),
    ],
)
def test_chunk_string(string, length, expected) -> None:
    got = chunk_string(string, length, acc=[])
    assert got == expected
