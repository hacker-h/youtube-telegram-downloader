# 🌐 Google Drive API Setup für rclone

Vollständige Anleitung zur Einrichtung von Google Drive mit rclone für automatische Cloud-Synchronisation.

## 📋 Übersicht

Diese Anleitung führt dich durch:
1. **Google Cloud Console Setup** - API aktivieren und OAuth konfigurieren
2. **rclone Konfiguration** - Verbindung zu Google Drive herstellen
3. **Docker Integration** - Automatische Synchronisation einrichten

## 🚀 Teil 1: Google Cloud Console Setup

### 1.1 Google Cloud Projekt erstellen

1. Öffne [Google Cloud Console](https://console.cloud.google.com/)
2. **Neues Projekt erstellen** oder bestehendes auswählen
3. Projektname: z.B. `YtTelegrmDownloaderProject`

### 1.2 Google Drive API aktivieren

1. **APIs & Services** → **Library**
2. Suche nach **"Google Drive API"**
3. **Google Drive API** auswählen
4. **Enable** klicken

### 1.3 OAuth Consent Screen konfigurieren

1. **APIs & Services** → **OAuth consent screen**
2. **External** auswählen (für persönliche Nutzung)
3. **App Information** ausfüllen:
   - App name: `YtTelegrmDownloaderProjectApp`
   - User support email: Deine E-Mail
   - Developer contact: Deine E-Mail
4. **Save and Continue**

### 1.4 Scopes hinzufügen

1. **Scopes** → **Add or Remove Scopes**
2. **Manually add scopes** → Folgende URL eingeben:
   ```
   https://www.googleapis.com/auth/drive.file
   ```
3. **Add to Table** → **Update**
4. **Save and Continue**

### 1.5 Test Users (Optional)

**Option A: Test User hinzufügen**
1. **Test users** → **Add users**
2. Deine E-Mail hinzufügen
3. **Save**

**Option B: App veröffentlichen**
1. **Publishing status** → **Publish App**
2. **Confirm** (keine Google-Verification nötig für persönliche Nutzung)

### 1.6 OAuth Credentials erstellen

1. **APIs & Services** → **Credentials**
2. **Create Credentials** → **OAuth 2.0 Client IDs**
3. **Application type**: `Desktop application`
4. **Name**: `youtube-telegram-downloader`
5. **Create**
6. **Download JSON** (optional, rclone nutzt Standard-Credentials)

## 🔧 Teil 2: rclone Konfiguration

### 2.1 Automatisches Setup (Empfohlen)

```bash
# Interaktives Setup-Script ausführen
./setup-rclone.sh
```

### 2.2 Manuelles Setup

```bash
# rclone Container mit Host-Netzwerk für OAuth
docker run -it --rm \
  --network host \
  -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest \
  config --config /config/rclone.conf
```

### 2.3 rclone Konfiguration Schritte

1. **New remote**: `n`
2. **Name**: `gdrive`
3. **Storage**: `15` (Google Drive)
4. **Client ID**: Enter (Standard verwenden)
5. **Client Secret**: Enter (Standard verwenden)
6. **Scope**: `3` (drive.file - Zugriff nur auf von rclone erstellte Dateien)
7. **Root folder**: Enter (Standard)
8. **Service account**: Enter (Standard)
9. **Auto config**: `Y` (Browser-OAuth)
10. **Team drive**: `n`
11. **Confirm**: `y`
12. **Quit**: `q`

### 2.4 OAuth Browser-Flow

1. **Browser öffnet sich automatisch** (dank `--network host`)
2. **Google Account auswählen**
3. **App-Berechtigung erteilen**:
   - "YtTelegrmDownloaderProjectApp möchte auf dein Google-Konto zugreifen"
   - **"Erlauben"** klicken
4. **Erfolg**: "The authentication flow has completed."

## 🧪 Teil 3: Konfiguration testen

### 3.1 Automatischer Test

```bash
# Test-Script ausführen
./test-rclone.sh
```

### 3.2 Manueller Test

```bash
# Verbindung testen
docker run --rm -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest \
  lsd gdrive: --config /config/rclone.conf

# Test-Datei hochladen
echo "Test" > data/gdrive/test.txt
docker run --rm \
  -v $(pwd)/rclone-config:/config \
  -v $(pwd)/data/gdrive:/data \
  rclone/rclone:latest \
  sync /data gdrive:/youtube-downloads \
  --config /config/rclone.conf
```

## 🐳 Teil 4: Docker Integration

### 4.1 Bot mit Google Drive starten

```bash
# Bot + rclone Google Drive Container
docker compose --profile gdrive up -d
```

### 4.2 Status prüfen

```bash
# Container Status
docker compose ps

# rclone Logs
docker compose logs rclone-gdrive

# Sync-Status
docker compose logs rclone-gdrive --tail=10
```

## 🔧 Troubleshooting

### Problem: "Zugriff blockiert" / "access_denied"

**Ursache**: OAuth Consent Screen nicht korrekt konfiguriert

**Lösung**:
1. **Scopes prüfen**: `https://www.googleapis.com/auth/drive.file` muss hinzugefügt sein
2. **Test User hinzufügen** oder **App veröffentlichen**
3. **Browser-Cache leeren** und OAuth erneut versuchen

### Problem: "network not found" beim Docker Start

**Ursache**: Docker-Netzwerk Probleme

**Lösung**:
```bash
docker compose down
docker system prune -f
docker compose --profile gdrive up -d
```

### Problem: Browser öffnet sich nicht

**Ursache**: `--network host` fehlt bei rclone config

**Lösung**:
```bash
# Setup-Script nutzen (hat --network host)
./setup-rclone.sh

# Oder manuell mit --network host
docker run -it --rm --network host \
  -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest \
  config --config /config/rclone.conf
```

### Problem: "Remote not found"

**Ursache**: Remote-Name stimmt nicht überein

**Lösung**:
```bash
# Verfügbare Remotes prüfen
docker run --rm -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest \
  listremotes --config /config/rclone.conf

# Remote muss "gdrive:" heißen
```

## 📁 Dateistruktur

Nach erfolgreichem Setup:

```
youtube-telegram-downloader/
├── rclone-config/
│   └── rclone.conf          # OAuth-Token und Konfiguration
├── data/
│   └── gdrive/              # Lokale Dateien für Google Drive Sync
├── rclone-logs/
│   └── sync.log             # Sync-Protokoll
├── setup-rclone.sh          # Automatisches Setup-Script
└── test-rclone.sh           # Test-Script
```

## 🔒 Sicherheit

### OAuth Scope `drive.file`

- ✅ **Sicher**: Zugriff nur auf von rclone erstellte Dateien
- ✅ **Sichtbar**: Dateien erscheinen normal in Google Drive
- ✅ **Widerrufbar**: Berechtigung kann jederzeit entzogen werden
- ❌ **Kein Zugriff** auf bestehende Google Drive Dateien

### Token-Verwaltung

- **Automatische Erneuerung**: rclone erneuert OAuth-Token automatisch
- **Sichere Speicherung**: Token in `rclone-config/rclone.conf`
- **Berechtigung entziehen**: [Google Account Permissions](https://myaccount.google.com/permissions)

## 🎯 Ergebnis

Nach erfolgreichem Setup:

1. **Bot speichert Downloads** in `data/gdrive/`
2. **rclone synct automatisch** alle 5 Minuten zu Google Drive
3. **Dateien erscheinen** in Google Drive unter `/youtube-downloads`
4. **Vollautomatisch** - keine weitere Interaktion nötig

## 📚 Weiterführende Links

- [Google Cloud Console](https://console.cloud.google.com/)
- [rclone Google Drive Dokumentation](https://rclone.org/drive/)
- [OAuth 2.0 Scopes für Google APIs](https://developers.google.com/identity/protocols/oauth2/scopes#drive) 