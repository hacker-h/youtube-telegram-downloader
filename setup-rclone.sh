#!/bin/bash

echo "🌐 rclone Google Drive Setup"
echo "============================"
echo

# Create directories
echo "📁 Creating directories..."
mkdir -p rclone-config rclone-logs
echo "✅ Directories created"
echo

# Check if config already exists
if [ -f "rclone-config/rclone.conf" ]; then
    echo "⚠️  rclone.conf already exists!"
    echo "Current remotes:"
    docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf
    echo
    read -p "Do you want to add another remote? (y/n): " add_remote
    if [ "$add_remote" != "y" ]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

echo "🔧 Starting rclone configuration..."
echo "This will open an interactive setup."
echo
echo "📋 Follow these steps:"
echo "1. Choose 'n' for new remote"
echo "2. Name: gdrive"
echo "3. Storage: Choose 'Google Drive' (usually number 15)"
echo "4. Client ID: Just press Enter (use default)"
echo "5. Client Secret: Just press Enter (use default)"
echo "6. Scope: Choose '3' for file access (recommended, more secure)"
echo "7. Root folder: Just press Enter (use default)"
echo "8. Service account: Just press Enter (use default)"
echo "9. Auto config: Choose 'Y' (this will open browser)"
echo "10. Team drive: Choose 'n' (unless you need it)"
echo "11. Confirm with 'y'"
echo "12. Choose 'q' to quit"
echo
read -p "Press Enter to start configuration..."

# Run interactive rclone config with host network for OAuth
docker run -it --rm \
  --network host \
  -v $(pwd)/rclone-config:/config \
  rclone/rclone:latest \
  config --config /config/rclone.conf

echo
echo "🔍 Checking configuration..."
if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf | grep -q "gdrive:"; then
    echo "✅ Google Drive remote 'gdrive' configured successfully!"
    
    echo
    echo "🧪 Testing connection..."
    if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest lsd gdrive: --config /config/rclone.conf > /dev/null 2>&1; then
        echo "✅ Connection test successful!"
    else
        echo "⚠️  Connection test failed. Check your configuration."
    fi
    
    echo
    echo "🚀 Ready to start with Google Drive sync:"
    echo "docker compose --profile gdrive up -d"
    
else
    echo "❌ Google Drive remote 'gdrive' not found!"
    echo "Please run the setup again and make sure to name the remote 'gdrive'"
fi 