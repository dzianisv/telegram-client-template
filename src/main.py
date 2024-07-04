#!/usr/bin/env python3

import sys
import logging
import re
import os
import subprocess
import time
import argparse
import json
from pyrogram import Client

class TelegramConfig:
    api_id=os.environ.get('TELEGRAM_APP_ID')
    api_hash=os.environ.get('TELEGRAM_APA_HASH')
    phone=os.environ.get('TELEGRAM_PHONE_NUMBER')
    session_name=os.environ.get('TELEGRAM_SESSION_ID')

logging.basicConfig(format="%(asctime)s %(message)s")
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stderr))

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json")
    args = parser.parse_args()

    config = TelegramConfig()
    app = Client(config.session_name, config.app_id, config.app_hash, phone_number=config.phone)

    @app.on_message()
    def handle_message(_client, message):
        for m in config.monitors:
            if message.chat.username != m.chat or not m.regex.match(message.text):
                continue

            # message https://docs.pyrogram.org/api/types/Message
            logger.debug("Received message %r", message)

            actions = []
            env = os.environ.copy()
            env["TELEGRAM_MESSAGE"] = message.text
            env["TELEGRAM_CHAT"] = message.chat.username
            for action in m.actions:
                actions.append(subprocess.Popen(["sh", "-c", action], env=env))

            for a in actions:
                a.wait()

    while True:
        try:
            logger.info("Started")
            app.run()
            break
        except KeyboardInterrupt:
            logging.info("Terminating...")
            break
        except Exception as e:
            logger.error(e)
            time.sleep(30)
            continue

main()