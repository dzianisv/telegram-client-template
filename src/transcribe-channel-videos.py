#!/usr/bin/env python3

import os
import subprocess
import telethon
from telethon import TelegramClient, events
from telethon.tl.types import InputMessagesFilterVideo
import requests
import logging

# Telegram API credentials
api_id = os.environ.get('TELEGRAM_API_ID')
api_hash = os.environ.get('TELEGRAM_API_HASH')
phone_number = os.environ.get('TELEGRAM_PHONE')
channel_username = 'DzianisPsycology'
whisperx_endpoint = os.environ.get("WHISPERX_ENDPOINT", "http://localhost:8080")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Initialize Telegram client
client = TelegramClient('tg', api_id, api_hash)

async def download_videos():
    await client.start(phone=phone_number)
    async for message in client.iter_messages(channel_username, filter=InputMessagesFilterVideo):
        if message.video and len(message.message) < 1:
            logger.info("Procssing video %s", message.video.id)
            video_path = await message.download_media()
            logger.info("Video downloaded to %s", video_path)
            audio_path = extract_audio(video_path)
            logger.info("Audio stream is located at %s", audio_path)
            transcription = transcribe(audio_path)
            logger.info("video %s transcription %s", message.video.id, transcription)
            await update_video_description(message, transcription)
            os.remove(video_path)
            os.remove(audio_path)

def extract_audio(video_path: str) -> str:
    audio_path = video_path.replace('.mp4', '.m4a')
    command = ['ffmpeg', '-i', video_path, '-vn', '-c:a', 'copy', audio_path]
    subprocess.run(command, check=True)
    return audio_path

def transcribe(audio_path: str) -> str:
    with open(audio_path, 'rb') as audio_file:
        files = {'audio_file': audio_file}
        response = requests.post(f"{whisperx_endpoint}/transcribe", files=files)
    response.raise_for_status()
    return response.json()['text']

def truncate(text: str) -> str:
    if len(text) > 385:
        return text[:385-3] + '...'
    else:
        return text

async def update_video_description(message, transcription: str):
    new_description = f"{message.message}\n{transcription}"
    try:
        await client.edit_message(message.chat_id, message.id, new_description)
    except telethon.errors.rpcerrorlist.MediaCaptionTooLongError as e:
        logger.warning(e)

def main():

    with client:
        client.loop.run_until_complete(download_videos())

if __name__ == "__main__":
    main()