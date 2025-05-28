import os
import logging
import shutil
from backends.storage_interface import StorageInterface


class LocalStorage(StorageInterface):
    """
    Local storage backend that keeps files in a local directory.
    This is essentially a "no-op" backend - files are already saved locally 
    by the downloader, so this just verifies they exist at the right place.
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
        Since this is a local storage, we just need to ensure the file exists.
        If the file is not already in the destination directory, we'll move it there.
        """
        # Extract just the filename without path
        file_name = os.path.basename(local_file_name)
        destination_path = os.path.join(self.destination_directory, file_name)

        # If the file is already in the right place, nothing to do
        if os.path.abspath(local_file_name) == os.path.abspath(destination_path):
            self.logger.info(f"File '{file_name}' is already in the destination directory")
            return

        # Otherwise, move the file to the destination directory
        self.logger.info(f"Moving '{local_file_name}' to '{destination_path}'")
        shutil.move(local_file_name, destination_path)
        self.logger.info(f"File moved successfully to local storage")

    def upload_multiple(self, files):
        """
        Move multiple files to the local storage directory.
        """
        for file in files:
            self.upload(file) 