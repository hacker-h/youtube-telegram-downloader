# youtube-telegram-downloader

This is a selfhosted [Telegram](https://telegram.org/) bot which downloads any videos or streams compatible with [yt-dlp](https://github.com/yt-dlp/yt-dlp).
The audiotrack of this video will be extracted and saved to your local storage.

# Getting Started

## Create your Telegram bot

Setting up your own Telegram bot is straight forward according to the [Telegram bots documentation](https://core.telegram.org/bots).

Insert the bot token you obtained during setup of your Telegram bot into the `bot.env` file.

Install the [Telegram Messenger](https://telegram.org/) on a system of your choice and search for your bot as a contact to create a conversation.

## (Option 1) Set up Local Storage

The bot uses local storage to save downloaded files. By default, files are stored in the `/home/bot/data` directory inside the container, 
which is mapped to the `./data` directory on your host system.

You can configure the storage location by setting the `LOCAL_STORAGE_DIR` environment variable in your `bot.env` file or in the 
`environment` section of the `docker-compose.yml` file.

## (Option 2) Set up Remote Storage (rclone)

Remote storage is supported via rclone in a separate container using shared volumes.
The example in docker-compose.yml uses google drive.

📖 **Setup Guide:** [docs/GOOGLE_DRIVE_SETUP.md](docs/GOOGLE_DRIVE_SETUP.md)

### Quick Setup
```bash
# Interactive Google Drive setup
./setup-rclone.sh

# Test the configuration
./test-rclone.sh

# Start with local storage backend only
docker compose up -d

# Start with Google Drive backend
docker compose --profile gdrive up -d
```


## Run the Telegram bot

Use the provided `docker-compose.yml` file:
```
git clone https://github.com/hacker-h/youtube-telegram-downloader.git &&\
cd youtube-telegram-downloader &&\
cp bot.env.default bot.env &&\
# Edit bot.env to add your BOT_TOKEN
docker-compose up -d
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
- `DEFAULT_STORAGE_BACKEND`: Skip storage selection and use this backend (optional, values: `local`, `gdrive`)
- `STORAGE_WARNING_THRESHOLD_GB`: Warning threshold in GB for low storage notifications (optional, default: `1`)

### Docker Compose Configuration

The `docker-compose.yml` file includes:
- Volume mount for persistent storage: `./data:/home/bot/data`
- Environment variable for storage directory: `LOCAL_STORAGE_DIR=/home/bot/data`

## Google Drive Cloud Storage Sync (Optional)

The docker-compose stack includes **Google Drive rclone sync service** for automatic cloud backup.

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
mkdir -p rclone-config rclone-logs
mkdir -p data/gdrive

# Configure Google Drive
docker run -it --rm \
  -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest \
  config --config /config/rclone.conf

# Start with Google Drive backend
docker compose --profile gdrive up -d
```

📖 **Setup Guide:** [docs/GOOGLE_DRIVE_SETUP.md](docs/GOOGLE_DRIVE_SETUP.md)

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
- [x] **Google Drive Cloud Storage Sync**
    - [x] Upload-only sync (files uploaded then deleted locally)
    - [x] Real-time file detection with inotify
    - [x] Comprehensive monitoring and logging
- [x] **Bot Commands**
    - [x] `/help` - Show comprehensive help
    - [x] `/ls` - List downloaded files
    - [x] `/search` - Search files by name
    - [x] `/whoami` - Show user ID
    - [x] `/storage` - Check storage space
- [x] Secure your bot against unauthorized access
- [x] Bot can be run as a Container Image
- [ ] Container Image available on Docker Hub



## Quick Start

### Prerequisites
- Docker and Docker Compose
- Telegram Bot Token
- (for Google Drive) proper rclone configuration

### Basic Setup
1. Clone the repository
2. Copy `bot.env.default` to `bot.env` and configure your bot token
3. Start with local storage: `docker compose up -d`

### Google Drive Setup
1. Configure rclone: `rclone config` (save to `./rclone-config/rclone.conf`)
2. Start with Google Drive: `docker compose --profile gdrive up -d`
3. The bot will automatically detect Google Drive backend

## Configuration

### Environment Variables
```bash
# Required
BOT_TOKEN=your_telegram_bot_token

# Optional
TRUSTED_USER_IDS=123456789,987654321  # Comma-separated user IDs
DEFAULT_OUTPUT_FORMAT=mp3             # Skip format selection
DEFAULT_STORAGE_BACKEND=gdrive        # Skip backend selection
LOCAL_STORAGE_DIR=/home/bot/data      # Storage directory
STORAGE_WARNING_THRESHOLD_GB=1        # Storage warning threshold in GB
```

### rclone Configuration
Place your rclone configuration in `./rclone-config/rclone.conf`:
```ini
[gdrive]
type = drive
client_id = your_client_id
client_secret = your_client_secret
token = {"access_token":"..."}
```

## Docker Profiles

### Local Storage Only
```bash
docker compose up -d
```

### With Google Drive Sync
```bash
docker compose --profile gdrive up -d
```

## File Structure
```
data/
├── local/           # Local storage files
└── gdrive/          # Google Drive sync directory

rclone-config/
└── rclone.conf      # rclone configuration

rclone-logs/
└── rclone-upload.log # Upload progress logs
```

## Commands

- **Send URL**: Send any YouTube URL to start download
- `/ls` - List files in storage backends
- `/search <query>` - Search for files by name
- `/storage` - Check storage status for all backends
- `/whoami` - Show your user information
- `/help` - Show help message



## Troubleshooting

### Upload Progress Not Working
- Check if rclone logs are accessible: `docker logs rclone-gdrive`
- Verify log file permissions: `ls -la rclone-logs/`
- Ensure inotify is working: Look for "File detected" messages

### Backend Not Detected
- Verify rclone.conf syntax: `rclone config show`
- Check file permissions: `chmod 644 rclone-config/rclone.conf`
- Restart containers: `docker compose restart`

### Slow Upload Progress
- Check rclone configuration and network speed
- Monitor with: `docker logs rclone-gdrive --follow`
- Adjust `RCLONE_CHECK_INTERVAL` for faster polling

## License

MIT License - see LICENSE file for details.

## 📚 Documentation

- **[Google Drive Setup Guide](docs/GOOGLE_DRIVE_SETUP.md)** - Detailed Google Drive configuration
- **[Setup Scripts](setup-rclone.sh)** - Interactive rclone configuration
- **[Test Scripts](test-rclone.sh)** - Connection testing and diagnostics
