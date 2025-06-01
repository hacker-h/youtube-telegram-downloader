import os
import time
import threading
import logging
import re
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class UploadProgressTracker:
    """
    Tracks upload progress for cloud storage backends by monitoring rclone logs
    and provides real-time updates to Telegram messages.
    """
    
    def __init__(self, bot, chat_id: int, message_id: int, backend: str, filename: str,
                 original_user_message_id: int = None, file_path: str = None, 
                 output_format: str = None, url: str = None, backend_name: str = None):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.backend = backend
        self.filename = filename
        
        # Additional info for final message
        self.original_user_message_id = original_user_message_id
        self.file_path = file_path
        self.output_format = output_format
        self.url = url
        self.backend_name = backend_name or backend
        
        # Progress tracking
        self.is_monitoring = False
        self.last_percent = 0
        self.last_update_time = 0
        self.upload_started = False
        self.upload_completed = False
        
        # Log file path (matches rclone container setup)
        self.log_file = "/logs/rclone-upload.log"
        
        # Thread for monitoring
        self.monitor_thread = None
        
    def start_monitoring(self, timeout: int = 300) -> None:
        """
        Start monitoring upload progress in a separate thread.
        
        Args:
            timeout: Maximum time to wait for upload completion (seconds)
        """
        if self.is_monitoring:
            logger.warning("Upload monitoring already started")
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_upload_progress,
            args=(timeout,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Started upload progress monitoring for {self.filename}")
        
    def stop_monitoring(self) -> None:
        """Stop monitoring upload progress."""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        logger.info(f"Stopped upload progress monitoring for {self.filename}")
        
    def _monitor_upload_progress(self, timeout: int) -> None:
        """
        Monitor rclone log file for upload progress of the specific file.
        
        Args:
            timeout: Maximum time to wait for upload completion
        """
        start_time = time.time()
        last_log_position = 0
        
        # Wait for log file to exist
        while not os.path.exists(self.log_file) and self.is_monitoring:
            if time.time() - start_time > 30:  # 30 second timeout for log file
                logger.warning(f"Log file {self.log_file} not found after 30 seconds")
                self._update_message("⚠️ Upload monitoring unavailable")
                return
            time.sleep(1)
            
        logger.info(f"Monitoring log file: {self.log_file}")
        
        while self.is_monitoring and (time.time() - start_time) < timeout:
            try:
                if os.path.exists(self.log_file):
                    with open(self.log_file, 'r') as f:
                        # Seek to last position to only read new lines
                        f.seek(last_log_position)
                        new_lines = f.readlines()
                        last_log_position = f.tell()
                        
                        # Process new log lines
                        for line in new_lines:
                            if self._process_log_line(line.strip()):
                                # Upload completed
                                return
                                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error monitoring upload progress: {e}")
                time.sleep(2)
                
        # Timeout reached
        if self.is_monitoring and not self.upload_completed:
            logger.warning(f"Upload monitoring timeout for {self.filename}")
            self._update_message("⏰ Upload monitoring timeout")
            
    def _process_log_line(self, line: str) -> bool:
        """
        Process a single log line and extract upload progress.
        
        Args:
            line: Log line to process
            
        Returns:
            True if upload completed, False otherwise
        """
        if not line or self.filename not in line:
            return False
            
        try:
            # Check for upload start
            if "📤 Uploading:" in line and self.filename in line:
                if not self.upload_started:
                    self.upload_started = True
                    self._update_message("☁️ Starting upload to cloud storage...")
                    logger.info(f"Upload started for {self.filename}")
                return False
                
            # Check for upload completion
            if "✅ Upload completed" in line and self.filename in line:
                self.upload_completed = True
                self._create_final_success_message()
                logger.info(f"Upload completed for {self.filename}")
                return True
                
            # Check for upload failure
            if "❌ Upload failed" in line and self.filename in line:
                self.upload_completed = True
                self._create_final_failure_message()
                logger.error(f"Upload failed for {self.filename}")
                return True
                
            # Parse rclone progress output
            # Look for patterns like "Transferred: 1.2M / 5.6M, 21%"
            progress_match = re.search(r'Transferred:.*?(\d+)%', line)
            if progress_match:
                percent = int(progress_match.group(1))
                self._update_progress(percent)
                
            # Look for transfer rate and ETA
            # Pattern: "Transferred: 1.2M / 5.6M, 21%, 500 kB/s, ETA 30s"
            detailed_match = re.search(
                r'Transferred:\s*([^,]+)\s*/\s*([^,]+),\s*(\d+)%(?:,\s*([^,]+))?(?:,\s*ETA\s*([^,\s]+))?',
                line
            )
            if detailed_match:
                transferred = detailed_match.group(1).strip()
                total = detailed_match.group(2).strip()
                percent = int(detailed_match.group(3))
                speed = detailed_match.group(4).strip() if detailed_match.group(4) else None
                eta = detailed_match.group(5).strip() if detailed_match.group(5) else None
                
                self._update_detailed_progress(percent, transferred, total, speed, eta)
                
        except Exception as e:
            logger.error(f"Error processing log line: {e}")
            
        return False
        
    def _update_progress(self, percent: int) -> None:
        """Update progress with percentage only."""
        current_time = time.time()
        
        # Only update if percentage changed significantly or enough time passed
        if abs(percent - self.last_percent) >= 10 or (current_time - self.last_update_time) >= 5:
            message = f"☁️ Uploading to {self.backend}... {percent}%"
            self._update_message(message)
            self.last_percent = percent
            self.last_update_time = current_time
            
    def _update_detailed_progress(self, percent: int, transferred: str, total: str, 
                                speed: Optional[str] = None, eta: Optional[str] = None) -> None:
        """Update progress with detailed information."""
        current_time = time.time()
        
        # Only update if percentage changed significantly or enough time passed
        if abs(percent - self.last_percent) >= 5 or (current_time - self.last_update_time) >= 3:
            message = f"☁️ Uploading to {self.backend}... {percent}%\n"
            message += f"📊 {transferred} / {total}"
            
            if speed:
                message += f" • {speed}"
            if eta and eta != "-":
                message += f" • ETA {eta}"
                
            self._update_message(message)
            self.last_percent = percent
            self.last_update_time = current_time
            
    def _update_message(self, text: str) -> None:
        """Update the Telegram message with new text."""
        try:
            self.bot.edit_message_text(
                text=text,
                chat_id=self.chat_id,
                message_id=self.message_id
            )
        except Exception as e:
            logger.warning(f"Failed to update upload progress message: {e}")
    
    def _create_final_success_message(self) -> None:
        """Create a comprehensive final success message and clean up original message."""
        try:
            # Create detailed success message
            message = "✅ **Download completed!**\n\n"
            message += f"📁 File: `{self.filename}`\n"
            
            if self.output_format:
                message += f"🎵 Format: {self.output_format.upper()}\n"
            
            message += f"💾 Backend: {self.backend_name}\n"
            
            if self.file_path:
                directory = os.path.dirname(self.file_path)
                message += f"📂 Location: `{directory}/`\n"
            
            message += f"☁️ Upload: ✅ Uploaded to {self.backend} successfully\n"
            
            if self.url:
                message += f"🔗 URL: {self.url[:50]}..."
            
            # Update the progress message with final status
            self.bot.edit_message_text(
                text=message,
                chat_id=self.chat_id,
                message_id=self.message_id,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Delete the original user message with the YouTube URL
            if self.original_user_message_id and self.original_user_message_id != self.message_id:
                try:
                    self.bot.delete_message(self.chat_id, self.original_user_message_id)
                    logger.info(f"Deleted original user message: {self.original_user_message_id}")
                except Exception as e:
                    logger.warning(f"Could not delete original user message: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to create final success message: {e}")
            # Fallback to simple message
            self._update_message("✅ Upload completed successfully!")
    
    def _create_final_failure_message(self) -> None:
        """Create a final failure message and clean up original message."""
        try:
            message = "❌ **Upload failed!**\n\n"
            message += f"📁 File: `{self.filename}`\n"
            message += f"💾 Backend: {self.backend_name}\n"
            message += f"☁️ Upload failed to {self.backend}\n\n"
            message += "The file was downloaded successfully but could not be uploaded to cloud storage."
            
            if self.url:
                message += f"\n🔗 URL: {self.url[:50]}..."
            
            # Update the progress message with failure status
            self.bot.edit_message_text(
                text=message,
                chat_id=self.chat_id,
                message_id=self.message_id,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Delete the original user message with the YouTube URL
            if self.original_user_message_id and self.original_user_message_id != self.message_id:
                try:
                    self.bot.delete_message(self.chat_id, self.original_user_message_id)
                    logger.info(f"Deleted original user message: {self.original_user_message_id}")
                except Exception as e:
                    logger.warning(f"Could not delete original user message: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to create final failure message: {e}")
            # Fallback to simple message
            self._update_message("❌ Upload failed")


class UploadProgressManager:
    """
    Manages multiple upload progress trackers and provides a simple interface
    for starting upload monitoring.
    """
    
    def __init__(self):
        self.active_trackers = {}
        
    def start_upload_monitoring(self, bot, chat_id: int, message_id: int, 
                              backend: str, filename: str, timeout: int = 300,
                              original_user_message_id: int = None, file_path: str = None,
                              output_format: str = None, url: str = None, 
                              backend_name: str = None) -> UploadProgressTracker:
        """
        Start monitoring upload progress for a file.
        
        Args:
            bot: Telegram bot instance
            chat_id: Chat ID for progress updates
            message_id: Message ID to update
            backend: Storage backend name
            filename: Name of file being uploaded
            timeout: Maximum monitoring time in seconds
            original_user_message_id: ID of original user message to delete
            file_path: Full path to the uploaded file
            output_format: Output format (mp3, mp4)
            url: Original YouTube URL
            backend_name: Display name of the backend
            
        Returns:
            UploadProgressTracker instance
        """
        # Stop any existing tracker for this file
        tracker_key = f"{chat_id}_{message_id}"
        if tracker_key in self.active_trackers:
            self.active_trackers[tracker_key].stop_monitoring()
            
        # Create and start new tracker
        tracker = UploadProgressTracker(
            bot, chat_id, message_id, backend, filename,
            original_user_message_id=original_user_message_id,
            file_path=file_path,
            output_format=output_format,
            url=url,
            backend_name=backend_name
        )
        self.active_trackers[tracker_key] = tracker
        tracker.start_monitoring(timeout)
        
        return tracker
        
    def stop_all_monitoring(self):
        """Stop all active upload monitoring."""
        for tracker in self.active_trackers.values():
            tracker.stop_monitoring()
        self.active_trackers.clear()


# Global instance for easy access
upload_progress_manager = UploadProgressManager() 