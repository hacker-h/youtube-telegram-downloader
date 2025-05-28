#!/bin/bash

# rclone sync script
# Environment variables:
# - SYNC_INTERVAL: Sync interval in seconds
# - REMOTE_NAME: Name of configured remote
# - REMOTE_PATH: Path on remote storage
# - SOURCE_DIR: Local directory to sync from

set -e

echo "Starting rclone sync service..."
echo "Remote: ${REMOTE_NAME}:${REMOTE_PATH}"
echo "Source: ${SOURCE_DIR}"
echo "Interval: ${SYNC_INTERVAL}s"

while true; do
    echo "[$(date)] Starting sync to ${REMOTE_NAME}:${REMOTE_PATH}"
    
    rclone sync "${SOURCE_DIR}" "${REMOTE_NAME}:${REMOTE_PATH}" \
        --config /config/rclone.conf \
        --log-file /logs/sync.log \
        --log-level INFO \
        --stats 1m \
        --stats-one-line \
        --exclude '*.tmp' \
        --exclude '*.part' \
        --exclude '.DS_Store' \
        --transfers 4 \
        --checkers 8
    
    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "[$(date)] Sync completed successfully"
    else
        echo "[$(date)] Sync failed with exit code $exit_code"
    fi
    
    echo "[$(date)] Waiting ${SYNC_INTERVAL} seconds..."
    sleep "${SYNC_INTERVAL}"
done 