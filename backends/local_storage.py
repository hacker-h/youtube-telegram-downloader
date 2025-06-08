import os
import logging
import shutil
from backends.storage_interface import StorageInterface


class LocalStorage(StorageInterface):
    """
    Local storage backend that keeps files in a local directory.
    This backend now respects the storage path and doesn't move files
    that are already in the correct location for their backend.
    """

    def __init__(self, destination_directory=None):
        """
        Initialize logging and local storage destination.
        """
        # Enable logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        
        # Use environment variable if set, otherwise use default
        self.destination_directory = destination_directory or os.getenv('LOCAL_STORAGE_DIR', './data')
        
        # Ensure directory exists
        os.makedirs(self.destination_directory, exist_ok=True)
        self.logger.info(f"LocalStorage initialized with directory: {self.destination_directory}")

    def upload(self, local_file_name):
        """
        For local storage, we just verify the file exists and is accessible.
        We DON'T move files that are already in backend-specific directories
        (like data/gdrive/, data/nextcloud/) to preserve cloud sync functionality.
        """
        # Check if file exists
        if not os.path.exists(local_file_name):
            self.logger.error(f"File not found: {local_file_name}")
            return

        # Extract just the filename without path
        file_name = os.path.basename(local_file_name)
        
        # Check if file is in a backend-specific subdirectory
        file_dir = os.path.dirname(os.path.abspath(local_file_name))
        base_data_dir = os.path.abspath(self.destination_directory)
        
        # If file is in a subdirectory of the data directory, leave it there
        # This preserves backend-specific routing (gdrive/, nextcloud/, etc.)
        if file_dir.startswith(base_data_dir) and file_dir != base_data_dir:
            self.logger.info(f"File '{file_name}' is in backend directory '{file_dir}', leaving it there for cloud sync")
            return
        
        # Only move files that are outside the data directory structure
        destination_path = os.path.join(self.destination_directory, file_name)
        
        # If the file is already in the main destination directory, nothing to do
        if os.path.abspath(local_file_name) == os.path.abspath(destination_path):
            self.logger.info(f"File '{file_name}' is already in the main destination directory")
            return

        # Move the file to the main destination directory (for local backend only)
        self.logger.info(f"Moving '{local_file_name}' to '{destination_path}'")
        shutil.move(local_file_name, destination_path)
        self.logger.info(f"File moved successfully to local storage")

    def upload_multiple(self, files):
        """
        Process multiple files for local storage.
        """
        for file in files:
            self.upload(file) 