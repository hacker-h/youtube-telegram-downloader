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

## Usage

1. Make sure that your bot is running as described in the previous steps.

2. Send the bot a link to a video you want to be downloaded, e.g. a Youtube URL.

3. Confirm the video the bot found on this URL by clicking `Download`.

4. Watch the bot downloading your video.

5. The bot converts the video to MP3 in highest quality available and confirms the accomplishment of this task with `Done!`.

More to be added according to the implemented features..

## Features

- [x] Interact with the user
- [x] Automatically download videos from URL provided via message
    - [ ] Code cleanup
    - [ ] Audio Quality selectable
    - [ ] Audio Format selectable
    - [ ] Audio Quality Default Value selectable
    - [ ] Audio Format Default Value selectable
- [ ] Automatically upload downloaded video to a remote backend
    - [ ] Google Drive
    - [ ] [Overcast](https://overcast.fm/)
- [ ] Secure your bot against unauthorized access
- [x] Bot can be run as a Container Image
- [ ] Container Image available on Docker Hub
