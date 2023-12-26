import os

import discord

API_KEY = os.getenv("DISCORD_BOT_API_KEY", "")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        print(f"message: {message}")
        await message.channel.send("Hello!")


if __name__ == "__main__":
    client.run(API_KEY)
