# 🌐 Google Drive API Setup for rclone

Complete guide for setting up Google Drive with rclone for automatic cloud synchronization.

## 📋 Overview

This guide will walk you through:
1. **Google Cloud Console Setup** - Enable API and configure OAuth
2. **rclone Configuration** - Establish connection to Google Drive
3. **Docker Integration** - Set up automatic synchronization

## 🚀 Part 1: Google Cloud Console Setup

### 1.1 Create Google Cloud Project

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. **Create new project** or select existing one
3. Project name: e.g., `YtTelegrmDownloaderProject`

### 1.2 Enable Google Drive API

1. **APIs & Services** → **Library**
2. Search for **"Google Drive API"**
3. Select **Google Drive API**
4. Click **Enable**

### 1.3 Configure OAuth Consent Screen

1. **APIs & Services** → **OAuth consent screen**
2. Select **External** (for personal use)
3. Fill out **App Information**:
   - App name: `YtTelegrmDownloaderProjectApp`
   - User support email: Your email
   - Developer contact: Your email
4. **Save and Continue**

### 1.4 Add Scopes

1. **Scopes** → **Add or Remove Scopes**
2. **Manually add scopes** → Enter the following URL:
   ```
   https://www.googleapis.com/auth/drive.file
   ```
3. **Add to Table** → **Update**
4. **Save and Continue**

### 1.5 Test Users (Optional)

**Option A: Add Test User**
1. **Test users** → **Add users**
2. Add your email
3. **Save**

**Option B: Publish App**
1. **Publishing status** → **Publish App**
2. **Confirm** (no Google verification needed for personal use)

### 1.6 Create OAuth Credentials

1. **APIs & Services** → **Credentials**
2. **Create Credentials** → **OAuth 2.0 Client IDs**
3. **Application type**: `Desktop application`
4. **Name**: `youtube-telegram-downloader`
5. **Create**
6. **Download JSON** (optional, rclone uses default credentials)

## 🔧 Part 2: rclone Configuration

### 2.1 Interactive rclone setup

```bash
# Run interactive setup script
./setup-rclone.sh
```

### 2.2 rclone Configuration Steps

1. **New remote**: `n`
2. **Name**: `gdrive` (or any name you prefer)
3. **Storage**: `15` (Google Drive)
4. **Client ID**: Enter (use default)
5. **Client Secret**: Enter (use default)
6. **Scope**: `3` (drive.file - access only to files created by rclone)
7. **Root folder**: Enter (default)
8. **Service account**: Enter (default)
9. **Auto config**: `Y` (browser OAuth)
10. **Team drive**: `n`
11. **Confirm**: `y`
12. **Quit**: `q`

### 2.3 OAuth Browser Flow

1. **rclone displays OAuth URL** - Copy the URL from the terminal output
2. **Open browser manually** and navigate to the OAuth URL (port available on localhost thanks to `--network host`)
3. **Select Google Account**
4. **Grant app permission**:
   - "YtTelegrmDownloaderProjectApp wants to access your Google Account"
   - Click **"Allow"**
5. **Success**: "The authentication flow has completed."

## 🧪 Part 3: Test Configuration

When the container is setup properly it should automatically upload and (locally) delete all files it detects in its data volume.

### 3.1 Automatic Test

```bash
# Run test script
./test-rclone.sh
```

### 3.2 Manual Test

```bash
# Test connection
docker run --rm -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest \
  lsd gdrive: --config /config/rclone.conf

# Upload test file
echo "Test" > data/gdrive/test.txt
docker run --rm \
  -v $(pwd)/rclone-config:/config \
  -v $(pwd)/data/gdrive:/data \
  rclone/rclone:latest \
  sync /data gdrive:/youtube-downloads \
  --config /config/rclone.conf
```

## 🐳 Part 4: Docker Integration

### 4.1 Start Bot with Google Drive

```bash
# Bot + rclone Google Drive container
docker compose --profile gdrive up -d
```

### 4.2 Check Status

```bash
# Container status
docker compose ps

# rclone logs
docker compose logs rclone-gdrive

# Sync status
docker compose logs rclone-gdrive --tail=10
```



## 🔧 Troubleshooting

### Problem: "Access blocked" / "access_denied"

**Cause**: OAuth Consent Screen not configured correctly

**Solution**:
1. **Check scopes**: `https://www.googleapis.com/auth/drive.file` must be added
2. **Add test user** or **publish app**
3. **Clear browser cache** and retry OAuth

### Problem: "network not found" on Docker start

**Cause**: Docker network issues

**Solution**:
```bash
docker compose down
docker system prune -f
docker compose --profile gdrive up -d
```

### Problem: Browser doesn't open

**Cause**: rclone is running within a container without a browser, therefore it cannot open your browser, however by sharing the host network namespace (make sure to use --network host) you will be able to access the exposed port locally by copying the logged URL into your browser e.g. http://localhost:31823
```

## 📁 File Structure

After successful setup:

```
youtube-telegram-downloader/
├── rclone-config/
│   └── rclone.conf          # OAuth token and configuration
├── data/
│   └── gdrive/              # Local files for Google Drive sync
├── rclone-logs/
│   └── sync.log             # Sync log
├── setup-rclone.sh          # Automatic setup script
└── test-rclone.sh           # Test script
```  

## 📚 Further Links

- [Google Cloud Console](https://console.cloud.google.com/)
- [rclone Google Drive Documentation](https://rclone.org/drive/)
- [OAuth 2.0 Scopes for Google APIs](https://developers.google.com/identity/protocols/oauth2/scopes#drive) 