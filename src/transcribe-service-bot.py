#!/usr/bin/env python3

import os
import logging
import subprocess
import requests
from telegram import Update, Chat, Chann
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WHISPERX_ENDPOINT = os.environ.get("WHISPERX_ENDPOINT", "http://localhost:8080")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Function to download video from Telegram
async def download_video(bot, file_id, file_path):
    new_file = await bot.get_file(file_id)
    await new_file.download_to_drive(file_path)

# Function to extract audio from video using ffmpeg
def extract_audio(video_file, audio_file):
    command = ["ffmpeg", "-i", video_file, "-q:a", "0", "-map", "a", audio_file]
    subprocess.run(command, check=True)

# Function to transcribe audio using WhisperX API
def transcribe(file: str, api_endpoint: str = WHISPERX_ENDPOINT) -> dict:
    logger.info("Transcribing file %s at %s", file, api_endpoint)
    with open(file, 'rb') as audio_file:
        files = {'audio_file': audio_file}
        response = requests.post(f"{api_endpoint}/transcribe", files=files)
    response.raise_for_status()
    return response.json()

# Function to process videos from the channel
async def process_videos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    chat_id = update.effective_message.chat_id

    async for message in bot.get_chat_history(chat_id):
        if message.video:
            video_file_id = message.video.file_id
            video_file_path = f"downloads/video_{video_file_id}.mp4"
            audio_file_path = f"downloads/audio_{video_file_id}.mp3"

            await download_video(bot, video_file_id, video_file_path)
            extract_audio(video_file_path, audio_file_path)

            transcription = transcribe(audio_file_path)
            transcription_text = transcription.get("text", "")

            # Update the video description
            new_caption = message.caption or ""
            new_caption += f"\n\nTranscription:\n{transcription_text}"

            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message.message_id,
                caption=new_caption,
                parse_mode=ParseMode.HTML
            )

            logger.info("Processed video: %s", video_file_path)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greets the user and records that they started a chat with the bot if it's a private chat.
    Since no `my_chat_member` update is issued when a user starts a private chat with the bot
    for the first time, we have to track it explicitly here.
    """
    if update.effective_message.text.startswith('/transcribe'):
        await update.effective_message.reply_text("Starting to process videos...")
        await process_videos(update, context)
        await update.effective_message.reply_text("Finished processing videos.")
    else:
        logger.info("Ignoring %s", update.effective_message.text)

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment variables.")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


    application.add_handler(MessageHandler(filters.ALL, handle_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()