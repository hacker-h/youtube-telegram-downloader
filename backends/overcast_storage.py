import requests
import bs4 as bs
import glob, os
import threading
from backends.storage_interface import StorageInterface

class OvercastStorage(StorageInterface):
    
    def __init__(self):
        self.OVERCAST_EMAIL = os.getenv('OVERCAST_EMAIL', None)
        self.OVERVAST_PASSWORD = os.getenv('OVERVAST_PASSWORD', None)


    def upload(self, file_path):
        if not file_path.endswith("mp3"):
            raise Exception("Only mp3 files can be uploaded.")

        with open(file_path, 'rb') as f:
            file_body = f.read()

        print("Sending: " + file_path + " Size: " + str(len(file_body)) + " bytes")
        filename = os.path.basename(file_path)
        r = requests.Session()

        payload = {'email': self.OVERCAST_EMAIL, 'password': self.OVERVAST_PASSWORD}
        r.post('https://overcast.fm/login', data=payload)
        data = r.get('https://overcast.fm/uploads').text

        soup = bs.BeautifulSoup(data, "html.parser")
        supa = soup.find('form', attrs={'id': 'upload_form'})

        action = supa.get('action')
        data_key_prefix = supa.get('data-key-prefix')

        bucket = supa.find('input', attrs={'name': 'bucket'}).get('value')
        key = supa.find('input', attrs={'name': 'key'}).get('value')
        aws_access_key_id = supa.find('input', attrs={'name': 'AWSAccessKeyId'}).get('value')
        acl = supa.find('input', attrs={'name': 'acl'}).get('value')
        upload_policy = supa.find('input', attrs={'name': 'policy'}).get('value')
        upload_signature = supa.find('input', attrs={'name': 'signature'}).get('value')
        upload_ctype = supa.find('input', attrs={'name': 'Content-Type'}).get('value')

        data_key_prefix += filename


        form_params = {
            "bucket": (None, bucket),
            "key": (None, key),
            "AWSAccessKeyId": (None, aws_access_key_id),
            "acl": (None, acl),
            "policy": (None, upload_policy),
            "signature": (None, upload_signature),
            "Content-Type": (None, upload_ctype),
            "file": (filename, file_body)
        }

        r.post(action, files=form_params)

        r.post('https://overcast.fm/podcasts/upload_succeeded', data={"key": data_key_prefix})

        print(file_path + " has been sent")

        if os.path.exists(file_path):
            os.remove(file_path)
    

    def upload_multiple(self, dir_path):
        os.chdir(dir_path)
        threads = []
        for filename in glob.glob("*"):
            if not filename.endswith("mp3"):
                continue
            t = threading.Thread(target=self.dir_path, args=(filename))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
    
