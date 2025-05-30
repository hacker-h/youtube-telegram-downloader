#!/bin/bash

echo "🌐 rclone Multi-Backend Setup"
echo "============================="
echo

# Create directories
echo "📁 Creating directories..."
mkdir -p rclone-config rclone-logs
mkdir -p data/local data/gdrive data/nextcloud data/proton
echo "✅ Directories created"
echo

# Check if config already exists
if [ -f "rclone-config/rclone.conf" ]; then
    echo "⚠️  rclone.conf already exists!"
    echo "Current remotes:"
    docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf
    echo
fi

# Backend selection menu
echo "🔧 Choose backend to configure:"
echo "1) Google Drive"
echo "2) Nextcloud"
echo "3) Proton Drive"
echo "4) Other (manual configuration)"
echo
read -p "Select backend (1-4): " backend_choice

case $backend_choice in
    1)
        BACKEND="gdrive"
        BACKEND_NAME="Google Drive"
        STORAGE_TYPE="drive"
        ;;
    2)
        BACKEND="nextcloud"
        BACKEND_NAME="Nextcloud"
        STORAGE_TYPE="webdav"
        ;;
    3)
        BACKEND="proton"
        BACKEND_NAME="Proton Drive"
        STORAGE_TYPE="protondrive"
        ;;
    4)
        echo "Starting manual configuration..."
        docker run -it --rm \
          --network host \
          -v $(pwd)/rclone-config:/config \
          rclone/rclone:latest \
          config --config /config/rclone.conf
        exit 0
        ;;
    *)
        echo "❌ Invalid selection"
        exit 1
        ;;
esac

echo
echo "🔧 Starting $BACKEND_NAME configuration..."
echo "This will open an interactive setup."
echo

# Backend-specific instructions
case $backend_choice in
    1)
        echo "📋 Google Drive Setup Steps:"
        echo "1. Choose 'n' for new remote"
        echo "2. Name: $BACKEND"
        echo "3. Storage: Choose 'Google Drive' (usually number 15)"
        echo "4. Client ID: Just press Enter (use default)"
        echo "5. Client Secret: Just press Enter (use default)"
        echo "6. Scope: Choose '3' for file access (recommended)"
        echo "7. Root folder: Just press Enter (use default)"
        echo "8. Service account: Just press Enter (use default)"
        echo "9. Auto config: Choose 'Y' (opens browser)"
        echo "10. Team drive: Choose 'n' (unless needed)"
        echo "11. Confirm with 'y'"
        echo "12. Choose 'q' to quit"
        ;;
    2)
        echo "📋 Nextcloud Setup Steps:"
        echo "1. Choose 'n' for new remote"
        echo "2. Name: $BACKEND"
        echo "3. Storage: Choose 'WebDAV' (usually number 42)"
        echo "4. URL: Enter your Nextcloud WebDAV URL"
        echo "   Format: https://your-nextcloud.com/remote.php/dav/files/USERNAME/"
        echo "5. Vendor: Choose '3' for Nextcloud"
        echo "6. User: Enter your Nextcloud username"
        echo "7. Password: Choose 'y' to enter password"
        echo "8. Enter your Nextcloud password"
        echo "9. Bearer token: Just press Enter (skip)"
        echo "10. Confirm with 'y'"
        echo "11. Choose 'q' to quit"
        echo
        echo "💡 Tip: You can find your WebDAV URL in Nextcloud:"
        echo "   Settings → Personal → Security → WebDAV"
        ;;
    3)
        echo "📋 Proton Drive Setup Steps:"
        echo "1. Choose 'n' for new remote"
        echo "2. Name: $BACKEND"
        echo "3. Storage: Choose 'Proton Drive' (usually number 35)"
        echo "4. Username: Enter your Proton account email"
        echo "5. Password: Enter your Proton account password"
        echo "6. 2FA: Enter your 2FA code if enabled"
        echo "7. Confirm with 'y'"
        echo "8. Choose 'q' to quit"
        echo
        echo "💡 Note: You may need to enable 2FA for Proton Drive access"
        ;;
esac

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
if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf | grep -q "$BACKEND:"; then
    echo "✅ $BACKEND_NAME remote '$BACKEND' configured successfully!"
    
    echo
    echo "🧪 Testing connection..."
    case $backend_choice in
        1|3)
            # For Google Drive and Proton Drive, test with lsd
            if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest lsd $BACKEND: --config /config/rclone.conf > /dev/null 2>&1; then
                echo "✅ Connection test successful!"
            else
                echo "⚠️  Connection test failed. Check your configuration."
            fi
            ;;
        2)
            # For Nextcloud, test with about command (more reliable)
            if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest about $BACKEND: --config /config/rclone.conf > /dev/null 2>&1; then
                echo "✅ Connection test successful!"
            else
                echo "⚠️  Connection test failed. Check your configuration."
                echo "Common issues:"
                echo "- Wrong WebDAV URL format"
                echo "- Incorrect username/password"
                echo "- App passwords required (check Nextcloud security settings)"
            fi
            ;;
    esac
    
    echo
    echo "🚀 Ready to start with $BACKEND_NAME sync:"
    echo "docker compose --profile $BACKEND up -d"
    
    echo
    echo "📊 Available commands:"
    echo "• Start bot with $BACKEND_NAME: docker compose --profile $BACKEND up -d"
    echo "• View $BACKEND_NAME logs: docker logs rclone-$BACKEND"
    echo "• Test connection: docker run --rm -v \$(pwd)/rclone-config:/config rclone/rclone:latest lsd $BACKEND: --config /config/rclone.conf"
    
else
    echo "❌ $BACKEND_NAME remote '$BACKEND' not found!"
    echo "Please run the setup again and make sure to name the remote '$BACKEND'"
fi

echo
echo "🔧 Want to configure another backend?"
echo "Run this script again to add more remotes to the same config file." 