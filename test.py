from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

def file_exists(drive, filename, parent_folder_id):
    existing_id = None
    existing_md5 = None
    file_list = drive.ListFile({'q':'trashed=false'}).GetList()
    for file in file_list:
        parents = file['parents'][0]
        parent_id = parents['id']
        if parent_id == folder_id:
            if file['title'] == filename:
                existing = True
                existing_id = file['id']
                existing_md5 = file['md5Checksum']
                break
    return existing_id, existing_md5

gauth = GoogleAuth()

drive = GoogleDrive(gauth)

dir_name = 'testDir'
filename = 'requirements.txt'

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# check whether the file already exists
folder_id = None
file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
for folder in file_list:
    if folder['title'] == dir_name:
        folder_id = folder['id']
        break

# create root folder if not existing
if folder_id is None:
    folder = drive.CreateFile({'title': dir_name,
    "mimeType": "application/vnd.google-apps.folder"})
    folder.Upload()
    folder_id = folder['id']


file_id, file_md5 = file_exists(drive, filename, folder_id)
if file_id is None:
    print("uploading new file")
    f = drive.CreateFile({"parents": [{"kind": "drive#fileLink", "id": folder_id}]})
    f.SetContentFile(filename)
    f.Upload()
else:
    # file already exists
    # check if md5sums differ => update the remote file

    print("updating existing file")
    print(file_id)
    print(file_md5)
