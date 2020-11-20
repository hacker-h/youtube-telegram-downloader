# tasks.py

import sys
import requests

import telegram
from backends import google_drive, overcast_storage
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Filters, MessageHandler, Updater
import logging
import os
import youtube_dl
from hurry.filesize import size
from backends import google_drive, overcast_storage
import telegram
from telegram_progress import tg_tqdm

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

class TaskData:
    def __init__(self, url, storage, selected_format, update) -> None:
        self.url = url
        self.storage = storage
        self.selected_format = selected_format
        self.update = update
        
class DownloadTask:
    def __init__(self) -> None:
        self.pbar = tg_tqdm("899962996:AAFvynxxYPDO62YJe4yZeu0fnB_n8TuDEA0", "885966540", total=100)

    def downloadVideo(self, taskData):
        """
        A stage downloading the selected media and converting it to the desired output format.
        Afterwards the file will be uploaded to the specified storage backend.
        """
        bot = telegram.Bot('899962996:AAFvynxxYPDO62YJe4yZeu0fnB_n8TuDEA0')
        logger.info("All settings: %s", taskData)
        logger.info("Video URL to download: '%s'", taskData.url)
        print(taskData.update["callback_query"].message)    # some default configurations for video downloads
        MP3_EXTENSION = 'mp3'
        YOUTUBE_DL_OPTIONS = {
            'format': taskData.selected_format,
            'restrictfilenames': True,
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': MP3_EXTENSION,
                'preferredquality': '192',
            }],
            'progress_hooks': [self.my_hook]
        }

        with youtube_dl.YoutubeDL(YOUTUBE_DL_OPTIONS) as ydl:
            result = ydl.extract_info("{}".format(taskData.url))
            original_video_name = ydl.prepare_filename(result)
        
        self.pbar.update(100)
        self.pbar.close()

        raw_media_name = os.path.splitext(original_video_name)[0]
        final_media_name = "%s.%s" % (raw_media_name, MP3_EXTENSION)

        # upload the file
        backend_name = taskData.storage
        backend = None
        if backend_name == CALLBACK_GOOGLE_DRIVE:
            backend = google_drive.GoogleDriveStorage()
        elif backend_name == CALLBACK_OVERCAST:
            backend = overcast_storage.OvercastStorage()
        else:
            logger.error("Invalid backend '%s'", backend)
        
        logger.info("Uploading the file..")
        backend.upload(final_media_name)
        

    def my_hook(self, d):
        if d['status'] == 'finished':
            self.pbar.update(100)
            self.pbar.close()
        if d['status'] == 'downloading':
            print("")
            print(float(d['_percent_str'].replace('%','')))
            self.pbar.update(float(d['_percent_str'].replace('%','')) - self.pbar.n)

if __name__ == "__main__":
   bot = telegram.Bot('899962996:AAFvynxxYPDO62YJe4yZeu0fnB_n8TuDEA0')
   reply = bot.send_message("885966540", "test")
   print(reply)
   bot.edit_message_text("kmd", "885966540", reply.message_id)