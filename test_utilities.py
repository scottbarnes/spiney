from sqlalchemy.orm import Session

from models import User
from test_models import db_session
from utilities import get_or_create_user


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
