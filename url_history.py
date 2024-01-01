import re
from datetime import datetime, timezone
from typing import Final, Sequence

import aiohttp
from lxml import etree
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from utilities import get_or_create_user

REGEX_BOTNICK: Final = r"(^<baubles.*?>)"
REGEX_NICK: Final = r"^<\d{0,}(.+?)>"
REGEX_DATETIME: Final = r"^(\[.*?\])"
compiled_regex_botnick = re.compile(REGEX_BOTNICK)
compiled_regex_nick = re.compile(REGEX_NICK)
compiled_regex_datetime = re.compile(REGEX_DATETIME)
STRPTIME_FORMAT: Final = "%Y-%m-%d %H:%M:%S"

from discord.member import Member

from models import Url, UrlTitle, User

#############
# URL parsing
#############


async def get_urls_from_line(line: str) -> list[str]:
    """
    Get string instance of a URL/link from a line of text.
    line1 = "song: https://youtu.be/Wjg3P8b13co?t=1. <3"
    >>> get_urls_from_line(line)
    [https://youtu.be/Wjg3P8b13co?t=1]
    """
    # Per https://www.tutorialspoint.com/how-to-use-python-regular-expression-to-extract-url-from-an-html-link
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    matched_urls = re.findall(url_pattern, line)
    strip_chars = ". ,:"
    return [url.strip(strip_chars) for url in matched_urls]


async def get_title_from_url(url: str) -> UrlTitle:
    """
    Return the <title> contents from a URL.
    url = "https://youtu.be/Wjg3P8b13co?t=1"
    >>> get_title_from_url(url)
    "が聴いたらどうなるのか　Cute Otters Hear Bird Whistle"
    """
    async with aiohttp.ClientSession() as session:
        response = await session.get(url, timeout=10)
        parser = etree.HTMLParser()
        tree = etree.HTML(await response.text(), parser)

        title = tree.find(".//title")
        if title is not None and title.text is not None:
            return UrlTitle(url=url, title=title.text.strip())
        else:
            return UrlTitle(url=url, title="")


async def add_urls_to_db(db_session: Session, author: Member, urls: list[UrlTitle]) -> None:
    """
    Take a `list[str]` of text URLs, create `Url` objects, and add to the database.
    """
    user = get_or_create_user(db_session=db_session, name=author.name, discord_id=author.id)
    urls = [Url(user=user, url=url.url, title=url.title, created=datetime.now(timezone.utc)) for url in urls]

    for url in urls:
        db_session.add(url)

    db_session.commit()


async def url_search(db_session: Session, term: str, user_id: int | None = None, limit: int = 10) -> Sequence[Url]:
    """
    Construct a query based on the function parameters and return the matching `Url`s.
    """
    db_query = select(Url).order_by(desc(Url.created)).limit(limit)

    if user_id and term:
        db_query = (
            select(Url).where(Url.url.like(f"%{term}%")).join(User).where(User.discord_id == user_id).limit(limit)
        )
    elif user_id:
        db_query = select(Url).join(User).where(User.discord_id == user_id).limit(limit)

    elif term:
        db_query = select(Url).where(Url.url.like(f"%{term}%")).limit(limit)

    if url_matches := db_session.execute(db_query).scalars().all():
        return url_matches
