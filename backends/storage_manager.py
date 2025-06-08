import os
import subprocess
import logging
import configparser
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages storage backends and routing based on available rclone remotes"""
    
    def __init__(self, rclone_config_path: str = "/home/bot/rclone-config/rclone.conf"):
        self.rclone_config_path = rclone_config_path
        self.local_storage_dir = os.getenv('LOCAL_STORAGE_DIR', '/home/bot/data')
        self.default_backend = os.getenv('DEFAULT_STORAGE_BACKEND', None)
        
    def get_available_backends(self) -> Dict[str, str]:
        """Get all available storage backends based on running containers"""
        backends = {"local": "Local Storage"}
        
        # Add only running rclone backends
        running_backends = self._get_running_rclone_backends()
        for backend in running_backends:
            backends[backend] = f"Cloud Storage ({backend})"
            
        return backends
    
    def _get_running_rclone_backends(self) -> List[str]:
        """Get list of currently running rclone backends by checking heartbeat files"""
        try:
            import time
            
            running_backends = []
            current_time = time.time()
            max_age = 30  # Heartbeat must be newer than 30 seconds
            
            # Check all subdirectories in data folder for heartbeat files
            data_dir = self.local_storage_dir
            if not os.path.exists(data_dir):
                return []
            
            for item in os.listdir(data_dir):
                item_path = os.path.join(data_dir, item)
                if not os.path.isdir(item_path):
                    continue
                
                # Skip local directory
                if item == 'local':
                    continue
                
                # Check for heartbeat file
                heartbeat_file = os.path.join(item_path, '.rclone-heartbeat')
                if os.path.exists(heartbeat_file):
                    try:
                        # Read timestamp from heartbeat file
                        with open(heartbeat_file, 'r') as f:
                            timestamp = float(f.read().strip())
                        
                        # Check if heartbeat is recent enough
                        if current_time - timestamp <= max_age:
                            running_backends.append(item)
                            logger.debug(f"Backend '{item}' is alive (heartbeat {current_time - timestamp:.1f}s ago)")
                        else:
                            logger.debug(f"Backend '{item}' heartbeat too old ({current_time - timestamp:.1f}s ago)")
                    except (ValueError, IOError) as e:
                        logger.debug(f"Invalid heartbeat file for '{item}': {e}")
                        
            logger.info(f"Found running rclone backends via heartbeat: {running_backends}")
            return running_backends
            
        except Exception as e:
            logger.error(f"Error checking heartbeat files: {e}")
            return []
    
    def _get_rclone_remotes(self) -> List[str]:
        """Parse rclone config and return available remotes (fallback method)"""
        if not os.path.exists(self.rclone_config_path):
            logger.info("No rclone config found, only local storage available")
            return []
            
        try:
            config = configparser.ConfigParser()
            config.read(self.rclone_config_path)
            
            # Get all sections (remotes) from rclone config
            remotes = [section for section in config.sections()]
            logger.info(f"Found rclone remotes in config: {remotes}")
            return remotes
            
        except Exception as e:
            logger.error(f"Error reading rclone config: {e}")
            return []
    
    def get_storage_path(self, backend: str) -> str:
        """Get the storage path for a given backend"""
        if backend == "local":
            # Local storage also gets its own subdirectory
            return os.path.join(self.local_storage_dir, "local")
        else:
            # For cloud backends, use subdirectory
            return os.path.join(self.local_storage_dir, backend)
    
    def ensure_storage_path(self, backend: str) -> str:
        """Ensure storage path exists and return it"""
        path = self.get_storage_path(backend)
        os.makedirs(path, exist_ok=True)
        return path
    
    def get_default_backend(self) -> Optional[str]:
        """Get the default backend if configured and running"""
        if self.default_backend:
            available = self.get_available_backends()
            if self.default_backend in available:
                return self.default_backend
            else:
                logger.warning(f"Default backend '{self.default_backend}' not available or not running")
        
        return None
    
    def should_ask_for_backend(self) -> bool:
        """Check if we should ask user for backend selection"""
        # If default backend is set and available, don't ask
        if self.get_default_backend():
            return False
            
        # If only local storage available, don't ask
        available = self.get_available_backends()
        if len(available) <= 1:
            return False
            
        return True
    
    def get_backend_display_name(self, backend: str) -> str:
        """Get display name for backend"""
        backends = self.get_available_backends()
        return backends.get(backend, backend)
    
    def is_cloud_backend(self, backend: str) -> bool:
        """Check if backend is a cloud storage and currently running"""
        return backend != "local" and backend in self._get_running_rclone_backends()
    
    def is_backend_running(self, backend: str) -> bool:
        """Check if a specific backend is currently running"""
        if backend == "local":
            return True  # Local is always available
        return backend in self._get_running_rclone_backends() 