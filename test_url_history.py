from dataclasses import dataclass
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from models import Url, UrlTitle
from test_models import db_session
from url_history import add_urls_to_db, get_title_from_url, get_urls_from_line

line1 = "And now you are gonna hear a song: https://youtu.be/Wjg3P8b13co?t=1. It is the song of my people."
line2 = "your song sucks. learn the songs of nature https://www.youtube.com/watch?v=LG0y9swWgm4 okay?"
line3 = "I try to <baubles> http://en.wikipedia.org/wiki/Moon_bridge, edge cases for https://www.greenfoothills.org/wp-content/uploads/2022/10/Burrowing-Owls-photo-credit-Wendy-Miller-featured-image.jpg fun and profit."
line4 = "You don't deserve all the things I have to add to this conversation."

url1 = "https://youtu.be/Wjg3P8b13co?t=1"
url2 = "https://www.youtube.com/watch?v=LG0y9swWgm4"
url3 = "http://en.wikipedia.org/wiki/Moon_bridge"
url4 = "https://www.greenfoothills.org/wp-content/uploads/2022/10/Burrowing-Owls-photo-credit-Wendy-Miller-featured-image.jpg"


@pytest.fixture
def mock_response(request):
    """
    Mock response for aiohttp.ClientSession.get("https://whatever").text(),
    but with async. See e.g. url_history.get_title_from_url() for an example.

    Note: `request` is special and the name cannot change.
    See https://docs.pytest.org/en/7.1.x/example/parametrize.html#indirect-parametrization.
    """

    class MockResponse:
        async def text(self):
            return request.param

    async def mock_get(*args, **kwargs):
        return MockResponse()

    return mock_get


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("url", "mock_response", "expected"),
    [
        (
            "https://example1.org",
            "<html><head><title>Mock Title</title></head><body></body></html>",
            UrlTitle(url="https://example1.org", title="Mock Title"),
        ),
        (
            "https://www.youtube.com?watch&v=1234&t=5",
            "<brokenhtml><title>が聴いたらどうなるのか　Cute Otters Hear Bird Whistle</title></brokenhtml></error>",
            UrlTitle(url="https://www.youtube.com?watch&v=1234&t=5", title="が聴いたらどうなるのか　Cute Otters Hear Bird Whistle"),
        ),
        (
            "https://example2.org",
            "<html><head><title>first title</title><title>second title</title></head></html>",
            UrlTitle(url="https://example2.org", title="first title"),
        ),
        (
            "https://example3.org",
            "<html><head><notitle>not a title</notitle></head></html>",
            UrlTitle(url="https://example3.org", title=""),
        ),
    ],
    indirect=["mock_response"],
)
async def test_get_title_from_url(url, mock_response, expected) -> None:
    """
    Use a mocked session to avoid network requests and to control the response
    value of the `.text()` method.
    """
    with patch("aiohttp.ClientSession.get", new=mock_response):
        result = await get_title_from_url(url)
        assert result == expected


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (line1, [url1]),
        (line2, [url2]),
        (line3, [url3, url4]),
        (line4, []),
    ],
)
async def test_get_urls_from_line(line, expected) -> None:
    got = await get_urls_from_line(line)
    assert got == expected


@pytest.mark.asyncio()
async def test_add_urls_to_db(db_session: Session) -> None:
    """Add URLs to the DB for a User."""

    @dataclass(slots=True)
    class Author:
        """Small test class until I figure out what the discord.py Author object is."""

        id: int
        name: str

    author = Author(name="Test User", id=1)
    url1 = UrlTitle(url="https://example.org?id=1", title="Example 1")
    url2 = UrlTitle(url="https://example.org?id=2", title="Example 2")
    urls = [url1, url2]

    assert db_session.query(Url).count() == 0
    await add_urls_to_db(db_session=db_session, author=author, urls=urls)
    assert db_session.query(Url).count() == 2
    second_url = db_session.query(Url).all()[1]
    assert second_url.user.name == "Test User"
    assert second_url.title == "Example 2"
    assert second_url.url == "https://example.org?id=2"
