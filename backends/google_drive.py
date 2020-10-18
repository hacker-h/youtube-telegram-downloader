from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import hashlib
import os


from backends.storage_interface import StorageInterface


class GoogleDriveStorage(StorageInterface):

    def __init__(self, path="testDir"):
        """
        Path to root folder, that will contain downloaded files
        """
        self.path = path
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        self.drive = GoogleDrive(gauth)

    def file_exists(self, filename, parent_folder_id):
        existing_id = None
        existing_md5 = None
        file_list = self.drive.ListFile({'q': 'trashed=false'}).GetList()
        for file in file_list:
            parents = file['parents'][0]
            parent_id = parents['id']
            if parent_id == parent_folder_id:
                if file['title'] == filename:
                    existing_id = file['id']
                    existing_md5 = file['md5Checksum']
                    break
        return existing_id, existing_md5

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

    def upload(self, filename):

        dir_name = 'testDir'
        # filename = 'requirements.txt'

        # check whether the file already exists
        folder_id = self.get_root_folder_id(dir_name)

        file_id, file_md5 = self.file_exists(filename, folder_id)
        if file_id is None:
            print("uploading new file")
            f = self.drive.CreateFile(
                {"parents": [{"kind": "drive#fileLink", "id": folder_id}]})
            f.SetContentFile(filename)
            f.Upload()
        else:
            # file already exists
            # TODO check if md5sums differ => update the remote file

            # TODO update remote file instead of uploading a copy
            print("updating existing file")
            print(file_id)
            print(file_md5)
