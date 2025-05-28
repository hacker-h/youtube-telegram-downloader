# tasks.py

import sys
import requests

import telegram
from telegram import update
from backends.local_storage import LocalStorage
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Filters, MessageHandler, Updater
import logging
import os
import yt_dlp
from hurry.filesize import size
import telegram
from dotenv import load_dotenv
import time


CALLBACK_MP4 = "mp4"
CALLBACK_MP3 = "mp3"
CALLBACK_LOCAL = "local"
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
    def __init__(self, url, storage, selected_format, update, output_format='mp3') -> None:
        self.url = url
        self.storage = storage
        self.selected_format = selected_format
        self.update = update
        self.output_format = output_format
        
class DownloadTask:
    def __init__(self, taskData) -> None:
        self.data = taskData
        
        # Handle both callback queries and direct messages
        if hasattr(self.data.update, 'callback_query') and self.data.update.callback_query:
            # From callback query (button click)
            self.chat_id = self.data.update.callback_query.message.chat.id
            self.old_message_id = self.data.update.callback_query.message.message_id
        else:
            # From direct message (immediate download)
            self.chat_id = self.data.update.message.chat.id
            self.old_message_id = self.data.update.message.message_id
            
        self.bot = telegram.Bot(BOT_TOKEN)
        self.progress_message_id = None
        self.pbar = None

    def downloadVideo(self):
        """
        Download the selected media, convert it to the desired output format,
        and save it to local storage.
        """
        try:
            # Send progress message with unique session identifier
            session_id = str(int(time.time()))[-4:]  # Last 4 digits of timestamp
            progress_msg = self.bot.send_message(self.chat_id, f"🔄 Starting download... (#{session_id})")
            self.progress_message_id = progress_msg.message_id
            
            # Initialize progress bar
            self.pbar = CustomProgressTracker(self.bot, self.chat_id, self.progress_message_id)

            logger.info("All settings: %s", self.data)
            logger.info("Video URL to download: '%s'", self.data.url)
            logger.info("Output format: '%s'", self.data.output_format)
            
            # Get the local storage directory from environment variable
            storage_dir = os.getenv('LOCAL_STORAGE_DIR', './data')
            
            # Configure yt-dlp options based on output format
            YT_DLP_OPTIONS = {
                'format': self.data.selected_format,
                'restrictfilenames': True,
                'outtmpl': f'{storage_dir}/%(title)s.%(ext)s',  # Save to configured storage directory
                'progress_hooks': [self.my_hook]
            }
            
            # Only add post-processors for MP3 (audio extraction)
            if self.data.output_format == 'mp3':
                YT_DLP_OPTIONS['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            # For MP4, we keep the video as-is (no post-processing needed)

            with yt_dlp.YoutubeDL(YT_DLP_OPTIONS) as ydl:
                result = ydl.extract_info("{}".format(self.data.url))
                original_video_name = ydl.prepare_filename(result)
            
            # Cleanup progress bar after download completes
            if self.pbar:
                self.pbar.close()
                self.pbar = None

            # Determine the final file name based on output format
            original_video_name = original_video_name.replace('/home/bot/', './')
            raw_media_name = os.path.splitext(original_video_name)[0]
            
            if self.data.output_format == 'mp3':
                final_media_name = f"{raw_media_name}.mp3"
            else:  # mp4 or keep original format
                # For MP4, the file might already have the correct extension from yt-dlp
                final_media_name = original_video_name
            
            logger.info(f"File downloaded to: {final_media_name}")

            # Update message to show saving progress
            self.bot.edit_message_text(f"💾 Saving file to local storage...", self.chat_id, self.progress_message_id)

            try:
                # Use local storage backend
                backend = LocalStorage()
                backend.upload(final_media_name)
                
                # Final success message
                filename = os.path.basename(final_media_name)
                self.bot.edit_message_text(
                    f"✅ Download completed!\n\n"
                    f"📁 File: {filename}\n"
                    f"🎵 Format: {self.data.output_format.upper()}\n"
                    f"📂 Location: {storage_dir}/\n"
                    f"🔗 URL: {self.data.url[:50]}...", 
                    self.chat_id, 
                    self.progress_message_id,
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Local storage failed: {e}")
                self.bot.edit_message_text(
                    f"❌ Error saving file: {final_media_name}\n"
                    f"Error: {str(e)[:100]}", 
                    self.chat_id, 
                    self.progress_message_id
                )
            
            # Delete the original message after processing (if it exists and is different)
            if hasattr(self, 'old_message_id') and self.old_message_id != self.progress_message_id:
                try:
                    self.bot.delete_message(self.chat_id, self.old_message_id)
                except Exception as e:
                    logger.warning(f"Could not delete original message: {e}")
                    
        except Exception as e:
            logger.error(f"Download failed: {e}")
            if self.progress_message_id:
                self.bot.edit_message_text(f"❌ Download failed: {str(e)[:100]}", self.chat_id, self.progress_message_id)
        finally:
            # Ensure progress bar is cleaned up
            if self.pbar:
                self.pbar.close()
                self.pbar = None

    def my_hook(self, d):
        if not self.pbar:
            return
            
        try:
            if d['status'] == 'finished':
                logger.info("Download finished, updating progress to 100%")
                # Show 100% completion
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes', total_bytes)
                self.pbar.update(100, downloaded_bytes, total_bytes)
                
            elif d['status'] == 'downloading':
                # Extract progress information from yt-dlp
                downloaded_bytes = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                
                # Calculate percentage
                if total_bytes and total_bytes > 0:
                    percent = (downloaded_bytes / total_bytes) * 100
                    self.pbar.update(percent, downloaded_bytes, total_bytes)
                elif '_percent_str' in d and d['_percent_str']:
                    # Fallback to yt-dlp's percentage if file size unknown
                    try:
                        percent = float(d['_percent_str'].replace('%', ''))
                        self.pbar.update(percent)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse progress percentage: {e}")
                        
        except Exception as e:
            logger.error(f"Error in progress hook: {e}")

class CustomProgressTracker:
    def __init__(self, bot, chat_id, message_id):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.last_percent = 0
        self.last_update_time = 0
        self.total_size = None
        self.downloaded_size = None
        
    def update(self, percent, downloaded_bytes=None, total_bytes=None):
        """Update progress with percentage and optional file size info"""
        current_time = time.time()
        
        # Only update if percentage changed by at least 5% or 2 seconds passed
        if abs(percent - self.last_percent) >= 5 or (current_time - self.last_update_time) >= 2:
            try:
                if downloaded_bytes and total_bytes:
                    downloaded_mb = downloaded_bytes / (1024 * 1024)
                    total_mb = total_bytes / (1024 * 1024)
                    progress_text = f"📥 Downloading... {percent:.0f}% ({downloaded_mb:.1f}/{total_mb:.1f}MB)"
                else:
                    progress_text = f"📥 Downloading... {percent:.0f}%"
                
                self.bot.edit_message_text(progress_text, self.chat_id, self.message_id)
                self.last_percent = percent
                self.last_update_time = current_time
                logger.info(f"Progress updated: {percent:.0f}%")
            except Exception as e:
                logger.warning(f"Failed to update progress message: {e}")
    
    def close(self):
        """Cleanup when download is finished"""
        pass

if __name__ == "__main__":
   bot = telegram.Bot('')
   reply = bot.send_message("", "")
   print(reply)
   bot.edit_message_text("", "", reply.message_id)