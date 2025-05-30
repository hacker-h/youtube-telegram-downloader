import os
import time
import logging
import subprocess
import shutil
import json
from typing import Dict, Optional, Tuple
import telegram

logger = logging.getLogger(__name__)

class StorageMonitor:
    """
    Monitors cloud storage space and sends Telegram notifications when storage is low.
    """
    
    def __init__(self, bot_token: str, rclone_config_path: str = "/home/bot/rclone-config/rclone.conf"):
        self.bot = telegram.Bot(bot_token)
        self.rclone_config_path = rclone_config_path
        
        # Storage threshold (in bytes) - only one warning level
        self.warning_threshold = int(os.getenv('STORAGE_WARNING_THRESHOLD_GB', '1')) * 1024 * 1024 * 1024  # Default 1GB
        
        logger.info(f"Storage monitor initialized - Warning threshold: {self.warning_threshold / (1024**3):.1f}GB")
    
    def check_storage_space(self, backend: str) -> Optional[Dict[str, int]]:
        """
        Check storage space for a specific backend using rclone.
        
        Args:
            backend: Backend name (e.g., 'gdrive', 'nextcloud')
            
        Returns:
            Dict with 'total', 'used', 'free' in bytes, or None if check failed
        """
        try:
            # Run rclone about command to get storage info
            cmd = [
                'docker', 'run', '--rm',
                '-v', f'{os.path.dirname(self.rclone_config_path)}:/config',
                'rclone/rclone:latest',
                'about', f'{backend}:',
                '--config', '/config/rclone.conf',
                '--json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"Failed to check storage for {backend}: {result.stderr}")
                return None
            
            # Parse JSON output
            data = json.loads(result.stdout)
            
            # Extract storage information
            storage_info = {
                'total': data.get('total', 0),
                'used': data.get('used', 0),
                'free': data.get('free', 0)
            }
            
            # If free space is not directly available, calculate it
            if storage_info['free'] == 0 and storage_info['total'] > 0:
                storage_info['free'] = storage_info['total'] - storage_info['used']
            
            logger.debug(f"Storage info for {backend}: {storage_info}")
            return storage_info
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout checking storage for {backend}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse storage info for {backend}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error checking storage for {backend}: {e}")
            return None
    
    def check_local_filesystem_space(self, path: str) -> Optional[Dict[str, int]]:
        """
        Check local filesystem space for a given path.
        
        Args:
            path: Local filesystem path
            
        Returns:
            Dict with 'total', 'used', 'free' in bytes, or None if check failed
        """
        try:
            # Get filesystem usage
            total, used, free = shutil.disk_usage(path)
            
            storage_info = {
                'total': total,
                'used': used,
                'free': free
            }
            
            logger.debug(f"Local filesystem info for {path}: {storage_info}")
            return storage_info
            
        except Exception as e:
            logger.error(f"Error checking local filesystem space for {path}: {e}")
            return None
    
    def format_storage_size(self, bytes_size: int) -> str:
        """Format bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"
    
    def check_and_notify(self, backend: str, chat_id: int, storage_path: str = None) -> bool:
        """
        Check storage space and send notification if needed.
        Always sends warning if storage is low (no tracking/throttling).
        
        Args:
            backend: Backend name to check
            chat_id: Telegram chat ID to send notifications to
            storage_path: Local path for local backend
            
        Returns:
            True if storage is sufficient, False if low
        """
        if backend == 'local':
            # Check local filesystem space
            if not storage_path:
                logger.warning("No storage path provided for local backend check")
                return True
            
            storage_info = self.check_local_filesystem_space(storage_path)
        else:
            # Check cloud storage space
            storage_info = self.check_storage_space(backend)
        
        if not storage_info:
            logger.warning(f"Could not check storage for {backend}")
            return True  # Assume OK if we can't check
        
        free_space = storage_info['free']
        total_space = storage_info['total']
        used_space = storage_info['used']
        
        # Calculate percentage used
        if total_space > 0:
            used_percentage = (used_space / total_space) * 100
        else:
            used_percentage = 0
        
        # Check if storage is low
        is_low = free_space <= self.warning_threshold
        
        if is_low:
            # Send warning notification
            self._send_warning_notification(backend, chat_id, storage_info, used_percentage)
            return False
        
        return True
    
    def _send_warning_notification(self, backend: str, chat_id: int, storage_info: Dict[str, int], used_percentage: float):
        """Send storage warning notification."""
        free_space_str = self.format_storage_size(storage_info['free'])
        total_space_str = self.format_storage_size(storage_info['total'])
        
        if backend == 'local':
            storage_type = "Local filesystem"
            icon = "💾"
        else:
            storage_type = f"{backend} cloud storage"
            icon = "☁️"
        
        message = (
            f"⚠️ **Storage Warning - {backend.upper()}**\n\n"
            f"{icon} Your {storage_type} is running low!\n\n"
            f"📊 **Storage Status:**\n"
            f"• Free space: {free_space_str}\n"
            f"• Total space: {total_space_str}\n"
            f"• Used: {used_percentage:.1f}%\n\n"
            f"💡 **Recommendation:**\n"
            f"Consider cleaning up old files or upgrading your storage.\n\n"
            f"🔧 **Warning threshold:** {self.format_storage_size(self.warning_threshold)}"
        )
        
        try:
            self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Sent storage warning for {backend} to chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send storage warning: {e}")
    
    def get_storage_status(self, backend: str, storage_path: str = None) -> Optional[str]:
        """
        Get formatted storage status for a backend.
        
        Args:
            backend: Backend name
            storage_path: Local path for local backend
            
        Returns:
            Formatted storage status string or None if check failed
        """
        if backend == 'local':
            if not storage_path:
                return None
            storage_info = self.check_local_filesystem_space(storage_path)
        else:
            storage_info = self.check_storage_space(backend)
        
        if not storage_info:
            return None
        
        free_space_str = self.format_storage_size(storage_info['free'])
        total_space_str = self.format_storage_size(storage_info['total'])
        used_space_str = self.format_storage_size(storage_info['used'])
        
        if storage_info['total'] > 0:
            used_percentage = (storage_info['used'] / storage_info['total']) * 100
            free_percentage = (storage_info['free'] / storage_info['total']) * 100
        else:
            used_percentage = 0
            free_percentage = 100
        
        # Determine status emoji
        if storage_info['free'] <= self.warning_threshold:
            status_emoji = "⚠️"
            status_text = "LOW"
        else:
            status_emoji = "✅"
            status_text = "OK"
        
        return (
            f"{status_emoji} **{backend.upper()} Storage ({status_text})**\n"
            f"• Free: {free_space_str} ({free_percentage:.1f}%)\n"
            f"• Used: {used_space_str} ({used_percentage:.1f}%)\n"
            f"• Total: {total_space_str}"
        )


# Global storage monitor instance
storage_monitor = None

def get_storage_monitor(bot_token: str) -> StorageMonitor:
    """Get or create global storage monitor instance."""
    global storage_monitor
    if storage_monitor is None:
        storage_monitor = StorageMonitor(bot_token)
    return storage_monitor 