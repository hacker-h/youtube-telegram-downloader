# tasks.py

import sys
import requests

import telegram
from telegram import update
from backends.google_drive import GoogleDriveStorage
from backends.overcast_storage import OvercastStorage
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Filters, MessageHandler, Updater
import logging
import os
import yt_dlp
from hurry.filesize import size
import telegram
from telegram_progress import tg_tqdm
from dotenv import load_dotenv


CALLBACK_MP4 = "mp4"
CALLBACK_MP3 = "mp3"
CALLBACK_OVERCAST = "overcast"
CALLBACK_GOOGLE_DRIVE = "drive"
CALLBACK_BEST_FORMAT = "best"
CALLBACK_SELECT_FORMAT = "select_format"
CALLBACK_ABORT = "abort"
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)
load_dotenv(dotenv_path='./bot.env')
BOT_TOKEN = os.getenv('BOT_TOKEN', None)
class TaskData:
    def __init__(self, url, storage, selected_format, update) -> None:
        self.url = url
        self.storage = storage
        self.selected_format = selected_format
        self.update = update
        
class DownloadTask:
    def __init__(self, taskData) -> None:
        self.data = taskData
        self.chat_id = self.data.update.callback_query.message.chat.id
        self.old_message_id = self.data.update.callback_query.message.message_id
        print(self.old_message_id)
        self.bot = telegram.Bot(BOT_TOKEN)

    def downloadVideo(self):
        """
        A stage downloading the selected media and converting it to the desired output format.
        Afterwards the file will be uploaded to the specified storage backend.
        """
        message_id = self.bot.send_message(self.chat_id, "Start Downloading").message_id
        self.pbar = tg_tqdm(BOT_TOKEN, self.chat_id, message_id,  desc="Downloading... ",total=100)


        logger.info("All settings: %s", self.data)
        logger.info("Video URL to download: '%s'", self.data.url)
        print(self.data.update["callback_query"].message)    # some default configurations for video downloads
        MP3_EXTENSION = 'mp3'
        YT_DLP_OPTIONS = {
            'format': self.data.selected_format,
            'restrictfilenames': True,
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': MP3_EXTENSION,
                'preferredquality': '192',
            }],
            'progress_hooks': [self.my_hook]
        }

        with yt_dlp.YoutubeDL(YT_DLP_OPTIONS) as ydl:
            result = ydl.extract_info("{}".format(self.data.url))
            original_video_name = ydl.prepare_filename(result)
        
        self.pbar.update(100)
        self.pbar.close()
        #self.bot.delete_message(self.pbar._TelegramIO.message_id, self.old_message_id)
        self.bot.edit_message_text(f"Uploading file to {self.data.storage}....", self.chat_id, message_id)

        raw_media_name = os.path.splitext(original_video_name)[0]
        final_media_name = "%s.%s" % (raw_media_name, MP3_EXTENSION)

        # upload the file
        backend_name = self.data.storage
        backend = None
        if backend_name == CALLBACK_GOOGLE_DRIVE:
            backend = GoogleDriveStorage()
        elif backend_name == CALLBACK_OVERCAST:
            backend = OvercastStorage()
        else:
            logger.error("Invalid backend '%s'", backend)
        
        logger.info("Uploading the file..")
        backend.upload(final_media_name)
        self.bot.edit_message_text(f"Your food is ready!🎉 \n \nurl: {self.data.url}\nstorage: {self.data.storage}\nformat: {self.data.selected_format}", self.chat_id, message_id )
        self.bot.delete_message(self.chat_id, self.old_message_id)
        

    def my_hook(self, d):
        if d['status'] == 'finished':
            self.pbar.update(100)
            self.pbar.close()
        if d['status'] == 'downloading':
            self.pbar.update(float(d['_percent_str'].replace('%','')) - self.pbar.n)

if __name__ == "__main__":
   bot = telegram.Bot('')
   reply = bot.send_message("", "")
   print(reply)
   bot.edit_message_text("", "", reply.message_id)