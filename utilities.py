import hashlib
import time

from pathlib import Path

import aiohttp

from aiohttp import ClientSession
from discord.ext.commands import MemberConverter
from sqlalchemy.orm import Session

from models import User


class ClientSessionFactory:
    """Singleton instance of an aiohttp ClientSession."""

    _session = None

    @classmethod
    async def get_session(cls) -> ClientSession:
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession()

        return cls._session


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


async def get_unique_filename(existing_filename: str) -> str:
    """Return `existing_filename` with a short, unique timestamp based hash as a prefix."""
    timestamp = str(time.time()).encode("utf-8")
    hash_object = hashlib.sha256(timestamp)
    hash_digest = hash_object.hexdigest()
    short_hash = hash_digest[:8]

    return f"{short_hash}-{existing_filename}"


async def download_file(url: str, filepath: str) -> None:
    """Download a file at `url` and save it to `filepath`."""
    session = await ClientSessionFactory.get_session()
    async with session.get(url) as response:
        if response.status == 200:
            with Path(filepath).open(mode="wb") as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
