#!/bin/sh

# rclone upload-only sync script with immediate file detection
# Uploads files immediately when detected and deletes them locally after successful upload

set -e

# Configuration
REMOTE_NAME="${RCLONE_REMOTE_NAME:-gdrive}"
REMOTE_PATH="${RCLONE_REMOTE_PATH:-youtube-downloads}"
LOCAL_PATH="${RCLONE_LOCAL_PATH:-/data/gdrive}"
LOG_FILE="${RCLONE_LOG_FILE:-/logs/rclone-upload.log}"
CHECK_INTERVAL="${RCLONE_CHECK_INTERVAL:-1}"  # Fallback check interval in seconds

# Ensure directories exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$LOCAL_PATH"

# Logging function
log() {
    echo "[$(date '+%a %b %d %H:%M:%S UTC %Y')] $1" | tee -a "$LOG_FILE"
}

# Upload a single file and delete it locally on success
upload_file() {
    local file_path="$1"
    local filename=$(basename "$file_path")
    
    log "📤 Uploading: $filename"
    
    # Upload file to remote
    if rclone copy "$file_path" "$REMOTE_NAME:$REMOTE_PATH" \
        --config /config/rclone.conf \
        --log-level INFO \
        --stats 1s \
        --progress 2>&1 | tee -a "$LOG_FILE"; then
        
        # Upload successful, delete local file
        if rm "$file_path"; then
            log "✅ Upload completed and local file deleted: $filename"
        else
            log "⚠️  Upload completed but failed to delete local file: $filename"
        fi
    else
        log "❌ Upload failed for: $filename"
        return 1
    fi
}

# Process all existing files in directory
process_existing_files() {
    log "🔍 Checking for existing files in $LOCAL_PATH"
    
    local file_count=0
    for file in "$LOCAL_PATH"/*; do
        # Skip if no files match the pattern
        [ -e "$file" ] || continue
        
        # Skip directories
        [ -f "$file" ] || continue
        
        upload_file "$file"
        file_count=$((file_count + 1))
    done
    
    if [ $file_count -eq 0 ]; then
        log "📂 No existing files found"
    else
        log "📊 Processed $file_count existing files"
    fi
}

# Monitor directory for new files using inotify
monitor_with_inotify() {
    log "👁️  Starting inotify monitoring on $LOCAL_PATH"
    
    # Monitor for file creation and moves (when files are moved into the directory)
    inotifywait -m -e close_write,moved_to "$LOCAL_PATH" --format '%w%f %e' 2>/dev/null | while read file event; do
        # Skip if not a regular file
        [ -f "$file" ] || continue
        
        log "🔔 File detected: $(basename "$file") (event: $event)"
        
        # Small delay to ensure file is completely written
        sleep 0.5
        
        # Upload the file
        upload_file "$file"
    done
}

# Fallback monitoring using periodic checks
monitor_with_polling() {
    log "⏰ Starting polling monitoring (every ${CHECK_INTERVAL}s) on $LOCAL_PATH"
    
    while true; do
        for file in "$LOCAL_PATH"/*; do
            # Skip if no files match the pattern
            [ -e "$file" ] || continue
            
            # Skip directories
            [ -f "$file" ] || continue
            
            log "🔔 File detected: $(basename "$file")"
            upload_file "$file"
        done
        
        sleep "$CHECK_INTERVAL"
    done
}

# Main execution
main() {
    log "🚀 Starting rclone upload-only sync service"
    log "📂 Local path: $LOCAL_PATH"
    log "☁️  Remote: $REMOTE_NAME:$REMOTE_PATH"
    log "📝 Log file: $LOG_FILE"
    
    # Test rclone configuration
    if ! rclone about "$REMOTE_NAME:" --config /config/rclone.conf >/dev/null 2>&1; then
        log "❌ Failed to connect to remote '$REMOTE_NAME'. Check configuration."
        exit 1
    fi
    
    log "✅ Remote connection verified"
    
    # Process any existing files first
    process_existing_files
    
    # Try to use inotify for real-time monitoring
    if command -v inotifywait >/dev/null 2>&1; then
        log "🎯 Using inotify for real-time file detection"
        monitor_with_inotify
    else
        log "⚠️  inotify-tools not available, falling back to polling"
        monitor_with_polling
    fi
}

# Handle signals gracefully
trap 'log "🛑 Received shutdown signal, exiting..."; exit 0' SIGTERM SIGINT

# Start the service
main 