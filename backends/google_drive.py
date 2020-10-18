from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import hashlib
import os


from backends.storage_interface import StorageInterface


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


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
        file_list = self.drive.ListFile({'q': 'trashed=false'}).GetList()
        file = None
        for file in file_list:
            parents = file['parents'][0]
            parent_id = parents['id']
            if parent_id == parent_folder_id:
                if file['title'] == filename:
                    return file
        return file

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

        dir_name = 'testDir'
        # file_name = 'requirements.txt'

        # check whether the file already exists
        folder_id = self.get_root_folder_id(dir_name)

        file = self.file_exists(local_file_name, folder_id)
        if file is None:
            print("uploading new file")
            f = self.drive.CreateFile(
                {"parents": [{"kind": "drive#fileLink", "id": folder_id}]})
            f.SetContentFile(local_file_name)
            f.Upload()
        else:
            # file already exists
            file_md5 = file['md5Checksum']

            # check if md5sums differ => update the remote file
            local_md5 = md5(local_file_name)
            if file_md5 == local_md5:
                print("file is already up to date")
            else:
                print("updating existing file..")
                # update remote file instead of uploading a copy
                file.SetContentFile(local_file_name)
                file.Upload()
                print("remote file updated")
