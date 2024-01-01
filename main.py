import argparse
import os
import shlex

import discord

from commands import get_current_weather
from models import get_db_session
from url_history import add_urls_to_db, get_title_from_url, get_urls_from_line, url_search

API_KEY = os.getenv("DISCORD_BOT_API_KEY", "")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
db_session = get_db_session()


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Debug line content
    if message:
        print(f"new message: {message}")
        print(f"new message content: {message.content}")
        print(f"new message author id: {message.author.id}")

    if message.content.startswith("$hello"):
        print(f"message: {message}")
        await message.channel.send("Hello!")

    # Current weather
    if message.content.startswith(".wz"):
        current_weather = await get_current_weather(message.content[len(".wz") + 1 :])
        await message.channel.send(current_weather)

    # Add to the URL history if a URL is mentioned.
    if urls := await get_urls_from_line(message.content):
        url_titles = [await get_title_from_url(url) for url in urls]
        await add_urls_to_db(db_session=db_session, author=message.author, urls=url_titles)

    # Url search.
    if message.content.startswith(".urlsearch"):
        command = message.content[len(".urlsearch") + 1 :]
        parser = argparse.ArgumentParser()
        parser.add_argument("-l", "--limit", type=int, help="Limit the search to the last n matches")
        parser.add_argument("-u", "--user", help="Search by user ID")
        parser.add_argument("term", nargs="?", default="", help="Search term")

        args = parser.parse_args(shlex.split(command))
        # Turn a mention of a Discord ID (e.g. `<@563953712273458518>` into an `int`)
        search_user_id = int(args.user.strip("><@")) if args.user else None

        urls = await url_search(db_session=db_session, term=args.term, user_id=search_user_id, limit=args.limit)
        if not urls:
            return None

        formatted_urls = [f"{url.url} ({url.title})\n" for url in urls]
        if formatted_urls:
            await message.channel.send("".join(url for url in formatted_urls))

        return None


if __name__ == "__main__":
    client.run(API_KEY)
