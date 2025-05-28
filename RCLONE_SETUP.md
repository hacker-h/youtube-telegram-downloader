# 🌐 rclone Cloud Storage Setup

Modulare Cloud-Storage Synchronisation mit separaten Containern pro Backend.

## 🏗️ Architektur

- **Modularer Ansatz**: Ein rclone Container pro Cloud-Backend
- **Volume-basiertes Routing**: Jeder Container überwacht sein eigenes Verzeichnis
- **Optionale Services**: Nur gewünschte Backends starten
- **Shared Script**: Gemeinsames Sync-Script für alle Container

## 🚀 Unterstützte Backends

- ✅ **Google Drive** (`rclone-gdrive`)
- ✅ **Nextcloud** (`rclone-nextcloud`) 
- ✅ **Proton Drive** (`rclone-proton`)
- ➕ **Erweiterbar** für weitere Backends

## 📋 Setup-Anleitung

### 1. Verzeichnisse erstellen
```bash
mkdir -p rclone-config rclone-logs scripts
mkdir -p data/gdrive data/nextcloud data/proton
```

### 2. rclone konfigurieren

```bash
# rclone Container für Konfiguration starten
docker run -it --rm \
  -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest \
  config --config /config/rclone.conf
```

**Wichtig**: Remote-Namen müssen mit den env-Dateien übereinstimmen:
- Google Drive: `gdrive`
- Nextcloud: `nextcloud`  
- Proton Drive: `proton`

### 3. Backend-spezifische Konfiguration

#### Google Drive
```bash
# rclone-gdrive.env anpassen
SYNC_INTERVAL=300
REMOTE_NAME=gdrive
REMOTE_PATH=/youtube-downloads
SOURCE_DIR=/data/gdrive
```

#### Nextcloud
```bash
# rclone-nextcloud.env anpassen
SYNC_INTERVAL=300
REMOTE_NAME=nextcloud
REMOTE_PATH=/youtube-downloads
SOURCE_DIR=/data/nextcloud
```

#### Proton Drive
```bash
# rclone-proton.env anpassen
SYNC_INTERVAL=300
REMOTE_NAME=proton
REMOTE_PATH=/youtube-downloads
SOURCE_DIR=/data/proton
```

### 4. Services starten

```bash
# Nur Bot (ohne Cloud-Sync)
docker-compose up -d youtube-telegram-downloader

# Mit Google Drive
docker-compose --profile gdrive up -d

# Mit Nextcloud
docker-compose --profile nextcloud up -d

# Mit mehreren Backends
docker-compose --profile gdrive --profile nextcloud up -d

# Alle Services
docker-compose --profile gdrive --profile nextcloud --profile proton up -d
```

## 🔧 Bot-Integration (Zukunft)

**Geplante Erweiterung**: Bot wählt Backend automatisch

```python
# Beispiel: Bot speichert je nach Nutzer-Wahl
if user_choice == "gdrive":
    download_path = "/home/bot/data/gdrive/"
elif user_choice == "nextcloud":
    download_path = "/home/bot/data/nextcloud/"
elif user_choice == "proton":
    download_path = "/home/bot/data/proton/"
```

## 📊 Monitoring

### Logs anzeigen
```bash
# Spezifischer Backend-Container
docker-compose logs -f rclone-gdrive
docker-compose logs -f rclone-nextcloud
docker-compose logs -f rclone-proton

# Alle rclone Services
docker-compose logs -f rclone-gdrive rclone-nextcloud rclone-proton

# Sync-Logs
tail -f rclone-logs/sync.log
```

### Status prüfen
```bash
# Aktive Container
docker-compose ps

# Nur rclone Services
docker-compose ps | grep rclone
```

## ⚙️ Erweiterte Konfiguration

### Neues Backend hinzufügen

1. **Env-Datei erstellen**: `rclone-BACKEND.env`
```bash
SYNC_INTERVAL=300
REMOTE_NAME=BACKEND
REMOTE_PATH=/youtube-downloads
SOURCE_DIR=/data/BACKEND
```

2. **Service in docker-compose.yml**:
```yaml
rclone-BACKEND:
    image: rclone/rclone:latest
    container_name: rclone-BACKEND
    profiles: ["BACKEND"]
    env_file:
        - './rclone-BACKEND.env'
    volumes:
        - ./data/BACKEND:/data/BACKEND:ro
        - ./rclone-config:/config:ro
        - ./rclone-logs:/logs
        - ./scripts/rclone-sync.sh:/usr/local/bin/rclone-sync.sh:ro
    command: ["/usr/local/bin/rclone-sync.sh"]
    restart: unless-stopped
    depends_on:
        - youtube-telegram-downloader
```

3. **Verzeichnis erstellen**: `mkdir -p data/BACKEND`

4. **Remote konfigurieren**: Name muss `BACKEND` sein

### Sync-Script anpassen

Das Script `scripts/rclone-sync.sh` kann für alle Backends angepasst werden:

```bash
# Zusätzliche rclone Flags
--transfers 8 \
--checkers 16 \
--bwlimit 50M \
--min-size 1M
```

## 🔒 Sicherheit

### Berechtigungen
```bash
chmod 700 rclone-config
chmod 600 rclone-config/rclone.conf
chmod +x scripts/rclone-sync.sh
```

### Read-Only Volumes
- Alle Source-Verzeichnisse sind read-only gemountet
- rclone.conf ist read-only
- Sync-Script ist read-only

## 🚨 Troubleshooting

### Container startet nicht
```bash
# Logs prüfen
docker-compose logs rclone-gdrive

# Env-Datei prüfen
cat rclone-gdrive.env

# Script-Berechtigungen
ls -la scripts/rclone-sync.sh
```

### Remote nicht gefunden
```bash
# Verfügbare Remotes auflisten
docker run --rm -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest listremotes --config /config/rclone.conf
```

### Sync-Fehler
```bash
# Manueller Test
docker run --rm \
  -v $(pwd)/rclone-config:/config \
  -v $(pwd)/data/gdrive:/data \
  rclone/rclone:latest \
  ls gdrive: --config /config/rclone.conf
```

## 📈 Performance-Tipps

1. **Separate Backends** für verschiedene Nutzer/Zwecke
2. **Unterschiedliche Sync-Intervalle** je nach Wichtigkeit
3. **Bandwidth-Limits** um Netzwerk nicht zu überlasten
4. **Parallele Transfers** für schnellere Uploads

## 🎯 Beispiel-Workflows

### Development Setup
```bash
# Nur lokaler Bot für Tests
docker-compose up -d youtube-telegram-downloader
```

### Production mit Google Drive
```bash
# Bot + Google Drive Sync
docker-compose --profile gdrive up -d
```

### Multi-Cloud Setup
```bash
# Bot + alle Cloud-Backends
docker-compose --profile gdrive --profile nextcloud --profile proton up -d
``` 