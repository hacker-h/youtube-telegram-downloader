# youtube-telegram-downloader

This is a selfhosted [Telegram](https://telegram.org/) bot which is supposed to download any Videos or Streams compatible with [youtube-dl](https://github.com/ytdl-org/youtube-dl).
The audiotrack of this video will be extracted and uploaded to one of your storage backends.

## Create your Telegram bot

Setting up your own Telegram bot is straight forward according to the [documentation](https://core.telegram.org/bots).

## Getting Started

Insert the bot token you obtained during setup of your Telegram bot into the `bot.env` file.
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

Run the bot:
```
python3 ./youtube-telegram-downloader/bot.py
```

More to be added according to the implemented features..

## Features

- [x] Interact with the user
- [ ] Automatically download videos from URL provided via message
    - [ ] Audio Quality selectable
    - [ ] Audio Format selectable
    - [ ] Audio Quality Default Value selectable
    - [ ] Audio Format Default Value selectable
- [ ] Automatically upload downloaded video to a remote backend
    - [ ] Google Drive
    - [ ] Overcast
- [ ] Bot can be run as a Container Image
- [ ] Container Image available on Docker Hub
