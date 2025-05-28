# youtube-telegram-downloader

This is a selfhosted [Telegram](https://telegram.org/) bot which downloads any videos or streams compatible with [yt-dlp](https://github.com/yt-dlp/yt-dlp).
The audiotrack of this video will be extracted and saved to your local storage.

# Getting Started

## Create your Telegram bot

Setting up your own Telegram bot is straight forward according to the [Telegram bots documentation](https://core.telegram.org/bots).

Insert the bot token you obtained during setup of your Telegram bot into the `bot.env` file.

Install the [Telegram Messenger](https://telegram.org/) on a system of your choice and search for your bot as a contact to create a conversation.

## Setting up Local Storage

The bot uses local storage to save downloaded files. By default, files are stored in the `/home/bot/data` directory inside the container, 
which is mapped to the `./data` directory on your host system.

You can configure the storage location by setting the `LOCAL_STORAGE_DIR` environment variable in your `bot.env` file or in the 
`environment` section of the `docker-compose.yml` file.

## Run the Telegram bot

### Option 1: as a Docker container (Recommended)
Use the provided `docker-compose.yml` file:
```
git clone https://github.com/hacker-h/youtube-telegram-downloader.git &&\
cd youtube-telegram-downloader &&\
cp bot.env.default bot.env &&\
# Edit bot.env to add your BOT_TOKEN
docker-compose up -d
```

### Option 2: on your system
Install [ffmpeg](https://ffmpeg.org/) on your system and make sure it is available in your [system PATH](https://en.wikipedia.org/wiki/PATH_(variable)).

Setup a python3 environment (e.g. with [virtualenv](https://virtualenv.pypa.io/en/stable/)) and source it.:
```
virtualenv -p python3.9 ~/.venv/youtube-telegram-downloader &&\
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

3. Choose `Download Best Format` or `Select Format`.

4. Choose `MP3` for audio or `MP4` for video.

5. Watch the bot downloading, converting and saving your file to the local storage directory.

6. Access your downloaded files in the `./data` directory on your host system.

## Configuration

### Environment Variables

- `BOT_TOKEN`: Your Telegram bot token (required)
- `TRUSTED_USER_IDS`: Comma-separated list of user IDs allowed to use the bot (optional, defaults to allowing anyone)
- `LOCAL_STORAGE_DIR`: Directory where downloaded files are stored (default: `/home/bot/data` in container, mapped to `./data` on host)
- `DEFAULT_OUTPUT_FORMAT`: Skip format selection and use this format (optional, values: `mp3`, `mp4`)
- `DEFAULT_STORAGE_BACKEND`: Skip storage selection and use this backend (optional, values: `local`, `gdrive`, `nextcloud`, `proton`)

### Docker Compose Configuration

The `docker-compose.yml` file includes:
- Volume mount for persistent storage: `./data:/home/bot/data`
- Environment variable for storage directory: `LOCAL_STORAGE_DIR=/home/bot/data`

## Cloud Storage Sync (Optional)

The docker-compose stack includes **modular rclone sync services** with separate containers per backend.

### Supported Backends
- ✅ **Google Drive** (`rclone-gdrive`)
- ✅ **Nextcloud** (`rclone-nextcloud`)
- ✅ **Proton Drive** (`rclone-proton`)
- ➕ **Easily extensible** for more backends

### Quick Setup
```bash
# Interactive Google Drive setup
./setup-rclone.sh

# Test the configuration
./test-rclone.sh

# Start with Google Drive sync
docker compose --profile gdrive up -d
```

### Manual Setup
```bash
# Create directories
mkdir -p rclone-config rclone-logs scripts
mkdir -p data/gdrive data/nextcloud data/proton

# Configure cloud storage
docker run -it --rm \
  -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest \
  config --config /config/rclone.conf

# Start with specific backend
docker compose --profile gdrive up -d
```

📖 **Setup Guides:**
- **Quick Setup:** [RCLONE_SETUP.md](RCLONE_SETUP.md) 
- **Google Drive API:** [docs/GOOGLE_DRIVE_SETUP.md](docs/GOOGLE_DRIVE_SETUP.md)

## Features

- [x] Interact with the user
- [x] Automatically download videos from URL provided via message
    - [x] Code cleanup
    - [x] Real-time progress tracking
    - [x] Intelligent error handling
    - [x] Fast URL validation
    - [x] **Dynamic storage backend selection**
    - [ ] Audio Quality selectable
    - [ ] Audio Format selectable
    - [ ] Audio Quality Default Value selectable
    - [ ] Audio Format Default Value selectable
    - [ ] Handle Video Playlists
    - [ ] Handle multiple URLs in one message
    - [ ] Use multiple threads for more performance
- [x] **Storage Backends**
    - [x] Local Storage (always available)
    - [x] **Dynamic backend detection** from rclone config
    - [x] **User choice per download** (if multiple backends available)
    - [x] **Default backend configuration** (skip selection)
    - [x] **Volume-based routing** (each backend has its own directory)
- [x] Automatically save downloaded content to local storage
    - [x] Local Storage
        - [x] Storage directory is configurable
- [x] **Cloud Storage Sync (NEW!)**
    - [x] Modular rclone architecture (docker-compose stack)
    - [x] Separate containers per backend (gdrive, nextcloud, proton)
    - [x] Volume-based routing and optional services
    - [x] Shared sync script and comprehensive monitoring
- [x] **Bot Commands**
    - [x] `/help` - Show comprehensive help
    - [x] `/ls` - List downloaded files
    - [x] `/search` - Search files by name
    - [x] `/whoami` - Show user ID
- [x] Secure your bot against unauthorized access
- [x] Bot can be run as a Container Image
- [ ] Container Image available on Docker Hub
