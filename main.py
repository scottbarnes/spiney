import os

import discord

from commands import get_current_weather
from models import get_db_session
from url_history import add_urls_to_db, get_title_from_url, get_urls_from_line

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
        current_weather = await get_current_weather(message.content[4:])
        await message.channel.send(current_weather)

    # Add to the URL history if a URL is mentioned.
    if urls := await get_urls_from_line(message.content):
        url_titles = [await get_title_from_url(url) for url in urls]
        await add_urls_to_db(db_session=db_session, author=message.author, urls=url_titles)


if __name__ == "__main__":
    client.run(API_KEY)
