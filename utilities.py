from discord.ext.commands import MemberConverter
from sqlalchemy.orm import Session

from models import User


def get_or_create_user(db_session: Session, name: str, discord_id: int | None = None) -> User:
    """Get or create a user."""
    if not discord_id and not name:
        raise ValueError("Need a discord_id or name.")

    user = (
        db_session.query(User).filter(User.discord_id == discord_id).first()
        or db_session.query(User).filter(User.name == name).first()
    )

    if not user:
        user = User(name=name, discord_id=discord_id)
        db_session.add(user)
        db_session.commit()

    return user


def get_user(db_session: Session, name: str = "", discord_id: int | None = None) -> User | None:
    """Get  user."""
    if not discord_id and not name:
        raise ValueError("Need a discord_id or name.")

    user = (
        db_session.query(User).filter(User.discord_id == discord_id).first()
        or db_session.query(User).filter(User.name == name).first()
    )

    return user


async def get_user_from_mention(ctx, mention):
    try:
        converter = MemberConverter()
        user = await converter.convert(ctx, mention)
        return user
    except Exception as e:
        await ctx.send(f"Error: {e}")
        return None
