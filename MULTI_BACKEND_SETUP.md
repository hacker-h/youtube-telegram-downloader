# Multi-Backend Setup Guide

This guide explains how to configure multiple cloud storage backends for the YouTube Telegram Downloader Bot.

## Supported Backends

- 💾 **Local Storage** (always available)
- 🔵 **Google Drive** (OAuth2)
- 🟠 **Nextcloud** (WebDAV)
- 🟣 **Proton Drive** (Username/Password + 2FA)

## Quick Setup

### 1. Interactive Setup Script
```bash
./setup-rclone.sh
```

The script will guide you through:
- Backend selection menu
- Step-by-step configuration instructions
- Connection testing
- Docker Compose commands

### 2. Test Configuration
```bash
./test-rclone.sh
```

This will test all configured backends and show available profiles.

## Manual Backend Configuration

### Google Drive Setup

1. **Run rclone config:**
```bash
docker run -it --rm --network host \
  -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest config --config /config/rclone.conf
```

2. **Configuration steps:**
   - Choose `n` for new remote
   - Name: `gdrive`
   - Storage: Choose `Google Drive` (usually #15)
   - Client ID/Secret: Press Enter (use defaults)
   - Scope: Choose `3` (file access)
   - Auto config: Choose `Y` (opens browser)
   - Complete OAuth2 flow in browser

3. **Start with Google Drive:**
```bash
docker compose --profile gdrive up -d
```

### Nextcloud Setup

1. **Get WebDAV URL:**
   - Go to Nextcloud → Settings → Personal → Security
   - Copy WebDAV URL (format: `https://your-nextcloud.com/remote.php/dav/files/USERNAME/`)

2. **Run rclone config:**
```bash
docker run -it --rm --network host \
  -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest config --config /config/rclone.conf
```

3. **Configuration steps:**
   - Choose `n` for new remote
   - Name: `nextcloud`
   - Storage: Choose `WebDAV` (usually #42)
   - URL: Enter your WebDAV URL
   - Vendor: Choose `3` for Nextcloud
   - Username: Your Nextcloud username
   - Password: Your Nextcloud password (or app password)

4. **Start with Nextcloud:**
```bash
docker compose --profile nextcloud up -d
```

### Proton Drive Setup

1. **Prerequisites:**
   - Proton account with Proton Drive access
   - 2FA enabled (recommended)

2. **Run rclone config:**
```bash
docker run -it --rm --network host \
  -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest config --config /config/rclone.conf
```

3. **Configuration steps:**
   - Choose `n` for new remote
   - Name: `proton`
   - Storage: Choose `Proton Drive` (usually #35)
   - Username: Your Proton email
   - Password: Your Proton password
   - 2FA: Enter 2FA code if enabled

4. **Start with Proton Drive:**
```bash
docker compose --profile proton up -d
```

## Multi-Backend Usage

### Start Multiple Backends
```bash
# Google Drive + Nextcloud
docker compose --profile gdrive --profile nextcloud up -d

# All backends
docker compose --profile gdrive --profile nextcloud --profile proton up -d
```

### Backend Selection in Bot
When multiple backends are configured:
1. Bot automatically detects available backends
2. User chooses backend for each download
3. Upload progress tracking works for all cloud backends

### File Structure
```
data/
├── local/           # Local storage (no sync)
├── gdrive/          # Google Drive sync
├── nextcloud/       # Nextcloud sync
└── proton/          # Proton Drive sync

rclone-config/
└── rclone.conf      # All backend configurations

rclone-logs/
└── rclone-upload.log # Shared upload logs
```

## Upload Progress Tracking

All cloud backends support real-time upload progress:
- 📊 Upload percentage
- 🚀 Transfer speed
- ⏱️ ETA
- 📁 File size information

### Example Progress Flow
```
🔄 Starting download... [001]
📥 Downloading... 45% (2.1/4.7MB)
💾 Moving file to Cloud Storage (nextcloud)...
☁️ Starting upload to cloud storage...
☁️ Uploading to nextcloud... 25%
📊 2.5 MiB / 10 MiB • 3.2 MB/s • ETA 2s
✅ Upload completed successfully!
```

## Environment Variables

### Default Backend (Optional)
Skip backend selection by setting a default:
```bash
# In bot.env
DEFAULT_STORAGE_BACKEND=nextcloud
```

### Available Values
- `local` - Local storage only
- `gdrive` - Google Drive
- `nextcloud` - Nextcloud
- `proton` - Proton Drive

## Monitoring and Logs

### View Upload Logs
```bash
# Google Drive
docker logs rclone-gdrive --follow

# Nextcloud
docker logs rclone-nextcloud --follow

# Proton Drive
docker logs rclone-proton --follow
```

### Check Backend Status
```bash
# Test all backends
./test-rclone.sh

# Manual connection test
docker run --rm -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest about nextcloud: --config /config/rclone.conf
```

## Troubleshooting

### Nextcloud Issues

**Connection Failed:**
- Verify WebDAV URL format
- Check username/password
- Try app password instead of main password
- Ensure WebDAV is enabled in Nextcloud

**App Password Setup:**
1. Nextcloud → Settings → Personal → Security
2. Create new app password
3. Use app password in rclone config

### Proton Drive Issues

**Authentication Failed:**
- Ensure 2FA is enabled
- Use correct email format
- Check Proton Drive subscription status

### General Issues

**Backend Not Detected:**
```bash
# Check config syntax
docker run --rm -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest config show --config /config/rclone.conf

# Fix permissions
chmod 644 rclone-config/rclone.conf

# Restart containers
docker compose restart
```

**Upload Progress Not Working:**
```bash
# Check logs are accessible
ls -la rclone-logs/

# Verify inotify is working
docker logs rclone-nextcloud | grep "File detected"
```

## Advanced Configuration

### Custom Remote Paths
Modify the remote path for each backend:
```yaml
# In docker-compose.yml
environment:
  - RCLONE_REMOTE_PATH=my-custom-folder
```

### Upload Intervals
Adjust file checking interval:
```yaml
environment:
  - RCLONE_CHECK_INTERVAL=5  # Check every 5 seconds
```

### Separate Log Files
Use different log files per backend:
```yaml
environment:
  - RCLONE_LOG_FILE=/logs/nextcloud-upload.log
```

## Security Considerations

### Credentials Storage
- rclone.conf contains encrypted credentials
- Mount as read-only in containers
- Backup configuration securely

### Network Security
- Use HTTPS for Nextcloud WebDAV
- Enable 2FA where supported
- Consider VPN for additional security

### Access Control
- Restrict bot access with `TRUSTED_USER_IDS`
- Use app passwords instead of main passwords
- Regular credential rotation

## Performance Tips

### Upload Optimization
- Use wired connection for large files
- Configure rclone transfer settings
- Monitor bandwidth usage

### Storage Management
- Regular cleanup of uploaded files
- Monitor cloud storage quotas
- Use compression for large files

## Migration

### Adding New Backend
1. Run `./setup-rclone.sh`
2. Choose new backend
3. Add to docker-compose profiles
4. Restart with new profile

### Removing Backend
1. Stop specific container: `docker compose stop rclone-nextcloud`
2. Remove from rclone.conf
3. Clean up data directory

### Backup Configuration
```bash
# Backup rclone config
cp rclone-config/rclone.conf rclone-config/rclone.conf.backup

# Restore from backup
cp rclone-config/rclone.conf.backup rclone-config/rclone.conf
```

## Storage Monitoring

The bot automatically monitors storage space and sends warnings when space is low.

### Features
- **Automatic monitoring** during downloads
- **Cloud storage monitoring** via rclone for all backends
- **Local filesystem monitoring** for local storage
- **Real-time warnings** sent via Telegram

### Configuration
Set the warning threshold in `bot.env`:
```bash
# Warning threshold in GB (default: 1 GB)
STORAGE_WARNING_THRESHOLD_GB=1
```

### How it Works
1. **Before each download**, the bot checks available storage space
2. **If space is low**, a warning message is sent to the user
3. **Download continues** after the warning (user is informed)
4. **For cloud backends**: Uses `rclone about` to check remote storage
5. **For local backend**: Checks local filesystem space

### Warning Messages
- **Cloud Storage**: "⚠️ Your gdrive cloud storage is running low!"
- **Local Storage**: "⚠️ Your Local filesystem is running low!"

### Manual Storage Check
Use the `/storage` command to manually check all configured backends:
```
/storage
```

This shows:
- **Free space** and **total space** for each backend
- **Usage percentage**
- **Status** (OK or LOW)
- **File count and directory size** (for local storage)

## Multi-Backend Preparation 