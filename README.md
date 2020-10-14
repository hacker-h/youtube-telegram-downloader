# youtube-telegram-downloader

This is a selfhosted [Telegram](https://telegram.org/) bot which is supposed to download any Videos or Streams compatible with [youtube-dl](https://github.com/ytdl-org/youtube-dl).
The audiotrack of this video will be extracted and uploaded to one of your storage backends.

## Create your Telegram bot

Setting up your own Telegram bot is straight forward according to the [Telegram bots documentation](https://core.telegram.org/bots).

## Getting Started

Insert the bot token you obtained during setup of your Telegram bot into the `bot.env` file.

Install [ffmpeg](https://ffmpeg.org/) on your system and make sure it is available in your [system PATH](https://en.wikipedia.org/wiki/PATH_(variable)).

Setup a python3 environment (e.g. with [virtualenv](https://virtualenv.pypa.io/en/stable/)) and source it.:
```
virtualenv -p python3 ~/.venv/youtube-telegram-downloader
source ~/.venv/youtube-telegram-downloader/bin/activate
```
Clone the repository and install all dependencies:
```
git clone https://github.com/hacker-h/youtube-telegram-downloader.git
pip3 install -r ./youtube-telegram-downloader/requirements.txt
```

Install the [Telegram Messenger](https://telegram.org/) on a system of your choice and search for your bot as a contact to create a conversation.

## Usage

1. Run the bot:
```
python3 ./youtube-telegram-downloader/bot.py
```

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
