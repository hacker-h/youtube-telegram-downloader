# youtube-telegram-downloader

This is a selfhosted [Telegram](https://telegram.org/) bot which is supposed to download any Videos or Streams compatible with [youtube-dl](https://github.com/ytdl-org/youtube-dl).
The audiotrack of this video will be extracted and uploaded to one of your storage backends.


# Getting Started

## Create your Telegram bot

Setting up your own Telegram bot is straight forward according to the [Telegram bots documentation](https://core.telegram.org/bots).

Insert the bot token you obtained during setup of your Telegram bot into the `bot.env` file.

Install the [Telegram Messenger](https://telegram.org/) on a system of your choice and search for your bot as a contact to create a conversation.

## Setting up your backend

### Google Drive
Follow the instructions on [setting up PyDrive Authentication](https://pythonhosted.org/PyDrive/quickstart.html#authentication).
Insert `client_id` and `client_secret` into the settings.yaml template:
```
# since this step is annoying to do manually, you can simply run this short shell script to do it
cp settings.yaml.example settings.yaml &&\
CLIENT_ID=$(cat client_secrets.json | grep client_id | cut -d'"' -f4)
CLIENT_SECRET=$(cat client_secrets.json | grep client_secret | cut -d'"' -f4)
sed -i "s/YOUR_CLIENT_ID/${CLIENT_ID}/g" settings.yaml &&\
sed -i "s/YOUR_CLIENT_SECRET/${CLIENT_SECRET}/g" settings.yaml
```

## Run the Telegram bot

### Option 1: as a Docker container
Use the provided `docker-compose.yml` file, which automatically mounts your configs into the container:
```
git clone https://github.com/hacker-h/youtube-telegram-downloader.git &&\
cd youtube-telegram-downloader &&\
docker-compose up -d
```

### Option 2: on your system
Install [ffmpeg](https://ffmpeg.org/) on your system and make sure it is available in your [system PATH](https://en.wikipedia.org/wiki/PATH_(variable)).

Setup a python3 environment (e.g. with [virtualenv](https://virtualenv.pypa.io/en/stable/)) and source it.:
```
virtualenv -p python3 ~/.venv/youtube-telegram-downloader &&\
source ~/.venv/youtube-telegram-downloader/bin/activate &&\

# Clone the repository and install all dependencies:
git clone https://github.com/hacker-h/youtube-telegram-downloader.git &&\
pip3 install -r ./youtube-telegram-downloader/requirements.txt &&\

# Run the bot:
python3 ./bot.py
```

## Secure your bot against unauthorized access
By default the bot trusts anybody sending messages to him hence `TRUSTED_USER_IDS` is unset (equivalent to absence of the environment variable).
To adapt this behaviour you can obtain your user id from the bot with the `whoami` command or 'whoami' as a plain text message.
Now add `TRUSTED_USER_IDS` to your `bot.env` file and set it to your user id or a comma separated list(CSV) of multiple user ids, e.g.:
```
TRUSTED_USER_IDS=12345,13579,24680
```
Note that if `TRUSTED_USER_IDS` is set the bot will not reply to any users which's ids are not contained; this also concerns the `whoami` command.

## Usage

1. Make sure that your bot is running as described in the previous steps.

2. Send the bot a link to a video you want to be downloaded, e.g. a Youtube URL.

3. Choose `Download Best Format`.

4. Choose `Audio`.

5. Choose `Google Drive`.

6. Watch the bot downloading, converting and uploading your video.

To be updated according to the implemented features..

## Features

- [x] Interact with the user
- [x] Automatically download videos from URL provided via message
    - [x] Code cleanup
    - [ ] Audio Quality selectable
    - [ ] Audio Format selectable
    - [ ] Audio Quality Default Value selectable
    - [ ] Audio Format Default Value selectable
    - [ ] Handle Video Playlists
    - [ ] Handle multiple URLs in one message
    - [ ] Use multiple threads for more performance
- [x] Automatically upload downloaded video to a remote backend
    - [x] Google Drive
        - [ ] remote directory path is configurable
    - [ ] [Overcast](https://overcast.fm/)
- [x] Secure your bot against unauthorized access
- [x] Bot can be run as a Container Image
- [ ] Container Image available on Docker Hub
