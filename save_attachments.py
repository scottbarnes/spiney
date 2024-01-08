from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

import discord
from models import Attachment
from utilities import download_file, get_or_create_user, get_unique_filename


async def get_message_from_reaction_payload(payload, client) -> Any:
    """
    Get the message from a reaction payload
    """
    channel_id = payload.channel_id
    message_id = payload.message_id

    channel = client.get_channel(channel_id)
    if channel is None:
        return

    try:
        message = await channel.fetch_message(message_id)
        print(f"type of message: {type(message)}", flush=True)

    except discord.NotFound:
        print(f"Error. Not found: {channel_id}")
        return

    except discord.Forbidden:
        print(f"Error. Forbidden: {channel_id}")

    except discord.HTTPException as e:
        print(f"Error. HTTP problem: {e}")

    assert message  # Discord raises an error when fetching if it's not found.
    return message


async def save_attachment(db_session: Session, client, payload, save_location: str = "/app/data/attachments") -> None:
    """
    Enter the attachment details into a database, and save the file to disk.
    """
    print(f"reaction added: {payload}")
    if payload.user_id == client.user.id:
        return

    # Look up the message associated with the reaction.
    message = await get_message_from_reaction_payload(payload, client)
    if not message.attachments:
        print("no attachment. returning")
        return

    # Only save attachments that are absent from the database.
    unsaved_attachments = []
    for attachment in message.attachments:
        db_query = select(Attachment).where(Attachment.discord_id == attachment.id)
        if saved_attachment := db_session.execute(db_query).scalar_one_or_none():
            continue
        unsaved_attachments.append(attachment)

    if not unsaved_attachments:
        print("No new attachments. Exiting.")
        return

    # Prepare each Attachmentn object for the database.
    user = get_or_create_user(db_session=db_session, name=payload.member.name, discord_id=payload.user_id)
    attachments = [
        Attachment(
            discord_filename=attachment.filename,
            discord_id=attachment.id,
            emoji=str(payload.emoji),
            filename=await get_unique_filename(attachment.filename),
            url=attachment.url,
            user=user,
        )
        for attachment in unsaved_attachments
    ]

    # Update the database.
    for attachment in attachments:
        db_session.add(attachment)

    db_session.commit()

    # Save attachments locally.
    for attachment in attachments:
        await download_file(url=str(attachment.url), filepath=f"{save_location}/{attachment.filename}")

    return None
