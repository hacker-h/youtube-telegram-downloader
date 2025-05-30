# tasks.py

import sys
import requests

import telegram
from telegram import update
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Filters, MessageHandler, Updater
import logging
import os
import yt_dlp
from hurry.filesize import size
import telegram
from dotenv import load_dotenv
import time
from backends.upload_progress import upload_progress_manager
from backends.storage_monitor import get_storage_monitor

# Global download counter for session IDs
download_counter = 0

# Session counter for unique progress tracking
session_counter = 0

def get_next_session_id():
    """Generate incremental session ID for downloads"""
    global session_counter
    session_counter += 1
    return f"[{session_counter:03d}]"

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
    def __init__(self, url, storage, selected_format, update, output_format='mp3', storage_manager=None) -> None:
        self.url = url
        self.storage = storage
        self.selected_format = selected_format
        self.update = update
        self.output_format = output_format
        self.storage_manager = storage_manager
        
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
        self.upload_tracker = None

    def downloadVideo(self):
        """
        Download the selected media, convert it to the desired output format,
        and save it to the configured storage backend.
        """
        try:
            # Send progress message with unique session identifier
            session_id = get_next_session_id()
            progress_msg = self.bot.send_message(self.chat_id, f"🔄 Starting download... {session_id}")
            self.progress_message_id = progress_msg.message_id
            
            # Initialize progress bar
            self.pbar = CustomProgressTracker(self.bot, self.chat_id, self.progress_message_id)

            logger.info("All settings: %s", self.data)
            logger.info("Video URL to download: '%s'", self.data.url)
            logger.info("Output format: '%s'", self.data.output_format)
            logger.info("Storage backend: '%s'", self.data.storage)
            
            # Always download to /tmp first, then move to correct backend directory
            temp_download_dir = "/tmp"
            
            # Get final storage path from storage manager
            if self.data.storage_manager:
                final_storage_dir = self.data.storage_manager.ensure_storage_path(self.data.storage)
                backend_name = self.data.storage_manager.get_backend_display_name(self.data.storage)
                is_cloud_backend = self.data.storage_manager.is_cloud_backend(self.data.storage)
                logger.info(f"Will download to {temp_download_dir} then move to: {backend_name} -> {final_storage_dir}")
            else:
                # Fallback to environment variable for local storage
                final_storage_dir = os.getenv('LOCAL_STORAGE_DIR', './data')
                backend_name = "Local Storage"
                is_cloud_backend = False
                logger.info(f"Will download to {temp_download_dir} then move to: {final_storage_dir}")
            
            # Check storage space for cloud backends before download
            if is_cloud_backend:
                storage_monitor = get_storage_monitor(BOT_TOKEN)
                
                # Update progress message to show storage check
                self.bot.edit_message_text(f"🔍 Checking {backend_name} storage space...", self.chat_id, self.progress_message_id)
                
                # Check storage and send notification if needed
                storage_ok = storage_monitor.check_and_notify(self.data.storage, self.chat_id)
                
                if not storage_ok:
                    # Storage is low, but continue with download (user has been warned)
                    logger.warning(f"Storage low for {self.data.storage}, but continuing with download")
                    
                    # Update message to show warning but continuing
                    self.bot.edit_message_text(
                        f"⚠️ {backend_name} storage is low, but continuing download...\n"
                        f"🔄 Starting download... {session_id}", 
                        self.chat_id, 
                        self.progress_message_id
                    )
                    time.sleep(2)  # Give user time to read the warning
                else:
                    logger.info(f"Storage check passed for {self.data.storage}")
            
            # Check local filesystem space for local backend
            elif self.data.storage == 'local':
                storage_monitor = get_storage_monitor(BOT_TOKEN)
                
                # Update progress message to show storage check
                self.bot.edit_message_text(f"🔍 Checking local filesystem space...", self.chat_id, self.progress_message_id)
                
                # Check local filesystem and send notification if needed
                storage_ok = storage_monitor.check_and_notify(self.data.storage, self.chat_id, final_storage_dir)
                
                if not storage_ok:
                    # Storage is low, but continue with download (user has been warned)
                    logger.warning(f"Local filesystem space low, but continuing with download")
                    
                    # Update message to show warning but continuing
                    self.bot.edit_message_text(
                        f"⚠️ Local filesystem space is low, but continuing download...\n"
                        f"🔄 Starting download... {session_id}", 
                        self.chat_id, 
                        self.progress_message_id
                    )
                    time.sleep(2)  # Give user time to read the warning
                else:
                    logger.info(f"Local filesystem check passed")
            
            # Configure yt-dlp options to download to /tmp
            YT_DLP_OPTIONS = {
                'format': self.data.selected_format,
                'restrictfilenames': True,
                'outtmpl': f'{temp_download_dir}/%(title)s.%(ext)s',  # Download to /tmp
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
            temp_file_path = original_video_name.replace('/home/bot/', './')
            raw_media_name = os.path.splitext(temp_file_path)[0]
            
            if self.data.output_format == 'mp3':
                temp_file_path = f"{raw_media_name}.mp3"
            else:  # mp4 or keep original format
                # For MP4, the file might already have the correct extension from yt-dlp
                pass  # temp_file_path is already correct
            
            logger.info(f"File downloaded to temp location: {temp_file_path}")

            # Update message to show moving to final storage
            self.bot.edit_message_text(f"💾 Moving file to {backend_name}...", self.chat_id, self.progress_message_id)

            try:
                # Move file from /tmp to final storage directory
                filename = os.path.basename(temp_file_path)
                final_file_path = os.path.join(final_storage_dir, filename)
                
                # Ensure final directory exists
                os.makedirs(final_storage_dir, exist_ok=True)
                
                # Move file to final location
                import shutil
                shutil.move(temp_file_path, final_file_path)
                logger.info(f"File moved from {temp_file_path} to {final_file_path}")
                
                # Start upload progress monitoring for cloud backends
                if is_cloud_backend:
                    logger.info(f"Starting upload progress monitoring for cloud backend: {self.data.storage}")
                    self.upload_tracker = upload_progress_manager.start_upload_monitoring(
                        bot=self.bot,
                        chat_id=self.chat_id,
                        message_id=self.progress_message_id,
                        backend=self.data.storage,
                        filename=filename,
                        timeout=300  # 5 minutes timeout
                    )
                    
                    # Wait a bit for upload to potentially complete
                    # The upload tracker will update the message automatically
                    time.sleep(2)
                    
                    # Check if upload completed quickly (small files)
                    if self.upload_tracker and not self.upload_tracker.upload_completed:
                        # For larger files, the upload tracker will continue monitoring
                        # and update the message when upload completes
                        logger.info(f"Upload monitoring active for {filename}")
                        return  # Let the upload tracker handle the final message
                
                # Determine cloud sync info
                cloud_info = ""
                if is_cloud_backend:
                    if self.upload_tracker and self.upload_tracker.upload_completed:
                        cloud_info = f"\n✅ Uploaded to {self.data.storage} successfully"
                    else:
                        cloud_info = f"\n☁️ Upload to {self.data.storage} in progress..."
                elif self.data.storage != 'local':
                    cloud_info = f"\n☁️ Cloud sync: Will be synced to {self.data.storage} automatically"
                
                # Final success message with backend info
                self.bot.edit_message_text(
                    f"✅ Download completed!\n\n"
                    f"📁 File: {filename}\n"
                    f"🎵 Format: {self.data.output_format.upper()}\n"
                    f"💾 Backend: {backend_name}\n"
                    f"📂 Location: {final_storage_dir}/"
                    f"{cloud_info}\n"
                    f"🔗 URL: {self.data.url[:50]}...", 
                    self.chat_id, 
                    self.progress_message_id,
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Error moving file to final storage: {e}")
                self.bot.edit_message_text(
                    f"❌ Error moving file to {backend_name}\n"
                    f"Temp file: {temp_file_path}\n"
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
                    
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"yt-dlp Download failed: {e}")
            if self.progress_message_id:
                # Interpret yt-dlp errors intelligently
                error_str = str(e).lower()
                if 'video unavailable' in error_str or 'private video' in error_str:
                    error_msg = "❌ Video unavailable!\n\nThis video is private, deleted, or restricted in your region."
                elif 'age-restricted' in error_str or 'sign in' in error_str:
                    error_msg = "❌ Age-restricted content!\n\nThis video requires sign-in or is age-restricted."
                elif 'copyright' in error_str or 'blocked' in error_str:
                    error_msg = "❌ Copyright blocked!\n\nThis video is blocked due to copyright restrictions."
                elif 'playlist' in error_str and 'empty' in error_str:
                    error_msg = "❌ Empty playlist!\n\nThis playlist is empty or all videos are unavailable."
                elif 'unsupported url' in error_str or 'no video formats' in error_str:
                    error_msg = "❌ Unsupported URL!\n\nThis platform or URL format is not supported by yt-dlp."
                elif 'network' in error_str or 'connection' in error_str:
                    error_msg = "❌ Network error!\n\nCannot connect to the video source. Please try again later."
                else:
                    error_msg = f"❌ Download failed!\n\n{str(e)[:150]}..."
                
                self.bot.edit_message_text(error_msg, self.chat_id, self.progress_message_id)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            if self.progress_message_id:
                self.bot.edit_message_text(f"❌ Unexpected error!\n\n{str(e)[:100]}...", self.chat_id, self.progress_message_id)
        finally:
            # Ensure progress bar is cleaned up
            if self.pbar:
                self.pbar.close()
                self.pbar = None

    def my_hook(self, d):
        """
        Progress hook for yt-dlp downloads.
        """
        if d['status'] == 'downloading':
            if self.pbar:
                try:
                    # Extract progress information
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    
                    if total_bytes > 0:
                        percent = (downloaded_bytes / total_bytes) * 100
                        self.pbar.update(percent, downloaded_bytes, total_bytes)
                    else:
                        # Fallback for when total size is unknown
                        self.pbar.update(0, downloaded_bytes, None)
                        
                except Exception as e:
                    logger.warning(f"Error updating download progress: {e}")
        
        elif d['status'] == 'finished':
            logger.info(f"Download finished: {d['filename']}")
            if self.pbar:
                self.pbar.update(100)

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