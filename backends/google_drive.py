from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import hashlib
import logging
import os

from backends.storage_interface import StorageInterface


def get_md5_sum(file_name):
    """
    Returns the MD5 check sum of a file.
    """
    file_hash = hashlib.md5()
    with open(file_name, "rb") as file_handle:
        # read file in chunks (memory efficient, works also for big files)
        while file_chunk := file_handle.read(4096):
            file_hash.update(file_chunk)
    return file_hash.hexdigest()


class GoogleDriveStorage(StorageInterface):
    DEFAULT_DESTINATION_ROOT="testDir"

    def __init__(self, destination_root_directory=DEFAULT_DESTINATION_ROOT):
        """
        Initialize logging and Google Drive authentication.
        """

        # Enable logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
        )

        self.logger = logging.getLogger(__name__)

        # self.destination_root_directory = destination_root_directory
        self.destination_root_directory = self.DEFAULT_DESTINATION_ROOT
        # TODO make directory name configurable
        # this will require a parsing of the directory path
        # all concerned subfolders will have to be looked up recursively in the file_exists function

        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        self.drive = GoogleDrive(gauth)

    def file_exists(self, file_name, parent_folder_id):
        """
        Checks whether a file exists in the respective parent folder.\n
        Returns its GoogleDriveFile object, otherwise None.
        """
        file_list = self.drive.ListFile({'q': 'trashed=false'}).GetList()
        for item in file_list:
            parents = item['parents'][0]
            parent_id = parents['id']
            if parent_id == parent_folder_id:
                if item['title'] == file_name:
                    return item
        return None

    def get_root_folder_id(self, parent_folder_name):
        file_list = self.drive.ListFile(
            {'q': "'root' in parents and trashed=false"}).GetList()
        for folder in file_list:
            if folder['title'] == parent_folder_name:
                folder_id = folder['id']
                break

        # create root folder if not existing
        if folder_id is None:
            folder = self.drive.CreateFile({'title': parent_folder_name,
                                            "mimeType": "application/vnd.google-apps.folder"})
            folder.Upload()
            folder_id = folder['id']
        return folder_id

    def upload(self, local_file_name):

        # check whether the file already exists
        folder_id = self.get_root_folder_id(self.destination_root_directory)

        file = self.file_exists(local_file_name, folder_id)
        if file is None:
            logging.info("uploading new file")
            f = self.drive.CreateFile(
                {"parents": [{"kind": "drive#fileLink", "id": folder_id}]})
            f.SetContentFile(local_file_name)
            f.Upload()
        else:
            # file already exists
            file_md5 = file['md5Checksum']

            # check if md5sums differ => update the remote file
            local_md5 = get_md5_sum(local_file_name)
            if file_md5 == local_md5:
                logging.info("file is already up to date")
            else:
                logging.info("updating existing file..")
                # update remote file instead of uploading a copy
                file.SetContentFile(local_file_name)
                file.Upload()
                logging.info("remote file updated")

    def upload_multiple(self, files):
        """
        Sequentially uploads multiple files to your Google Drive backend.
        """
        # TODO use multiple threads to do this concurrently
        for file in files:
            self.upload(file)
