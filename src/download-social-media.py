#!/usr/bin/env python3

import os
import subprocess
import telethon
import re
from telethon import TelegramClient, events
from telethon.tl.types import InputMessagesFilterVideo
import requests
import logging
import asyncio
from telethon import TelegramClient, events
from yt_dlp import YoutubeDL
from urllib.parse import urlparse

# Telegram API credentials
api_id = os.environ.get('TELEGRAM_API_ID')
api_hash = os.environ.get('TELEGRAM_API_HASH')
phone_number = os.environ.get('TELEGRAM_PHONE')
whisperx_endpoint = os.environ.get("WHISPERX_ENDPOINT", "http://localhost:8080")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Initialize Telegram client
client = TelegramClient('tg', api_id, api_hash)

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

def truncate_video_description(text: str) -> str:
    if len(text) > 385:
        return text[:385-3] + '...'
    else:
        return text

async def download_video(url: str, video_id: str) -> str:
    parsed_url = urlparse(url)

    ydl_opts = {
        'cookies': "./cookies.txt",
        'format': 'best',
        'outtmpl': f'{parsed_url.hostname}-{video_id}.%(ext)s',
        'noplaylist': True,
        'quiet': True,
    }
    logger.info("yt-dlp options: %r", ydl_opts)

    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_duration = info_dict.get('duration', 0)
        if video_duration <= 300:
            return ydl.prepare_filename(info_dict)
        else:
            raise ValueError("Video is longer than 5 minutes")

@client.on(events.NewMessage(incoming=True, outgoing=True))
async def handler(event):
    message = event.message.message
    url_pattern = re.compile(r'(https?://\S+)')
    urls = url_pattern.findall(message)

    for url in urls:

        if any(domain in message for domain in ['youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com']):
            url = message
            files = []
            try:
                video_path = await download_video(url, event.message.id)
                files.append(video_path)
                logger.info(f"Downloaded video to: {video_path}")
                audio_path = extract_audio(video_path)
                files.append(audio_path)
                logger.info(f"Extracted audio to: {audio_path}")
                logger.info("Transcribing...")
                transcription = transcribe(audio_path)
                logger.info(f"Transcription: {transcription}")

                logger.info("Uploading video to chat %s", event.chat_id)
                await client.send_file(event.chat_id, video_path, video_note=True, supports_streaming=True, caption=truncate_video_description(transcription), reply_to=event.message.id)
            except Exception as e:
                logger.error(f"Error processing video: {e}")
            finally:
                for file in files:
                    os.remove(file)

async def main():
    await client.start()
    logger.info("Client is running...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())