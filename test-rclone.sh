#!/bin/bash

echo "🧪 rclone Google Drive Test"
echo "==========================="
echo

# Check if config exists
if [ ! -f "rclone-config/rclone.conf" ]; then
    echo "❌ No rclone.conf found!"
    echo "Run ./setup-rclone.sh first"
    exit 1
fi

echo "📋 Available remotes:"
docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf
echo

# Check if gdrive remote exists
if ! docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf | grep -q "gdrive:"; then
    echo "❌ 'gdrive' remote not found!"
    echo "Run ./setup-rclone.sh to configure Google Drive"
    exit 1
fi

echo "🔍 Testing Google Drive connection..."
if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest lsd gdrive: --config /config/rclone.conf; then
    echo "✅ Google Drive connection successful!"
else
    echo "❌ Google Drive connection failed!"
    exit 1
fi

echo
echo "📁 Creating test file..."
echo "Test file created at $(date)" > data/gdrive/test-sync.txt

echo "🚀 Testing sync to Google Drive..."
if docker run --rm \
  -v $(pwd)/rclone-config:/config \
  -v $(pwd)/data/gdrive:/data \
  rclone/rclone:latest \
  sync /data gdrive:/youtube-downloads \
  --config /config/rclone.conf \
  --progress; then
    echo "✅ Sync test successful!"
else
    echo "❌ Sync test failed!"
    exit 1
fi

echo
echo "🔍 Verifying file on Google Drive..."
if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest ls gdrive:/youtube-downloads --config /config/rclone.conf | grep -q "test-sync.txt"; then
    echo "✅ File found on Google Drive!"
    echo
    echo "🧹 Cleaning up test file..."
    docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest delete gdrive:/youtube-downloads/test-sync.txt --config /config/rclone.conf
    rm -f data/gdrive/test-sync.txt
    echo "✅ Cleanup complete!"
else
    echo "❌ File not found on Google Drive!"
fi

echo
echo "🎉 rclone Google Drive setup is working!"
echo "Start with: docker compose --profile gdrive up -d" 