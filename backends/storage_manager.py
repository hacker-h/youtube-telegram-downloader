import os
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
        """Get all available storage backends"""
        backends = {"local": "Local Storage"}
        
        # Add rclone remotes if config exists
        rclone_remotes = self._get_rclone_remotes()
        for remote in rclone_remotes:
            backends[remote] = f"Cloud Storage ({remote})"
            
        return backends
    
    def _get_rclone_remotes(self) -> List[str]:
        """Parse rclone config and return available remotes"""
        if not os.path.exists(self.rclone_config_path):
            logger.info("No rclone config found, only local storage available")
            return []
            
        try:
            config = configparser.ConfigParser()
            config.read(self.rclone_config_path)
            
            # Get all sections (remotes) from rclone config
            remotes = [section for section in config.sections()]
            logger.info(f"Found rclone remotes: {remotes}")
            return remotes
            
        except Exception as e:
            logger.error(f"Error reading rclone config: {e}")
            return []
    
    def get_storage_path(self, backend: str) -> str:
        """Get the storage path for a given backend"""
        if backend == "local":
            return self.local_storage_dir
        else:
            # For cloud backends, use subdirectory
            return os.path.join(self.local_storage_dir, backend)
    
    def ensure_storage_path(self, backend: str) -> str:
        """Ensure storage path exists and return it"""
        path = self.get_storage_path(backend)
        os.makedirs(path, exist_ok=True)
        return path
    
    def get_default_backend(self) -> Optional[str]:
        """Get the default backend if configured"""
        if self.default_backend:
            available = self.get_available_backends()
            if self.default_backend in available:
                return self.default_backend
            else:
                logger.warning(f"Default backend '{self.default_backend}' not available")
        
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
        """Check if backend is a cloud storage"""
        return backend != "local" and backend in self._get_rclone_remotes() 