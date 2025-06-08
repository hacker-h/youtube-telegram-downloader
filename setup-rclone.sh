#!/bin/bash

echo "🌐 rclone Dynamic Backend Setup"
echo "==============================="
echo "This script helps you configure rclone with any remote name you choose."
echo

# Create directories
echo "📁 Creating directories..."
mkdir -p rclone-config rclone-logs
mkdir -p data/local  # Always create local directory
echo "✅ Basic directories created"
echo

# Check if config already exists
if [ -f "rclone-config/rclone.conf" ]; then
    echo "⚠️  rclone.conf already exists!"
    echo "Current remotes:"
    docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf 2>/dev/null || echo "No remotes found or config invalid"
    echo
    read -p "Do you want to add another remote to existing config? (y/n): " add_remote
    if [ "$add_remote" != "y" ] && [ "$add_remote" != "Y" ]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Backend selection menu
echo "🔧 Choose backend type to configure:"
echo "1) Google Drive"
echo "2) Nextcloud/WebDAV"
echo "3) Proton Drive"
echo "4) Other backend (manual configuration)"
echo "5) List available backends and test connections"
echo
read -p "Select option (1-5): " backend_choice

case $backend_choice in
    5)
        echo
        echo "📋 Listing current remotes and testing connections..."
        if [ -f "rclone-config/rclone.conf" ]; then
            remotes=$(docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf 2>/dev/null)
            if [ -z "$remotes" ]; then
                echo "No remotes configured yet."
            else
                echo "Found remotes:"
                for remote in $remotes; do
                    remote_name=${remote%:}
                    echo -n "• $remote_name: "
                    if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest about $remote --config /config/rclone.conf >/dev/null 2>&1; then
                        echo "✅ Connected"
                    else
                        echo "❌ Connection failed"
                    fi
                done
            fi
        else
            echo "No rclone config found. Run setup first."
        fi
        echo
        read -p "Press Enter to continue with setup..."
        exec "$0"  # Restart the script
        ;;
    1)
        BACKEND_TYPE="drive"
        BACKEND_NAME="Google Drive"
        STORAGE_TYPE="drive"
        ;;
    2)
        BACKEND_TYPE="webdav"
        BACKEND_NAME="Nextcloud/WebDAV"
        STORAGE_TYPE="webdav"
        ;;
    3)
        BACKEND_TYPE="protondrive"
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
        
        echo
        echo "🔍 Checking what remotes were added..."
        if [ -f "rclone-config/rclone.conf" ]; then
            remotes=$(docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf 2>/dev/null)
            if [ -n "$remotes" ]; then
                echo "✅ Available remotes:"
                for remote in $remotes; do
                    remote_name=${remote%:}
                    echo "• $remote_name"
                    # Create directory for each remote
                    mkdir -p "data/$remote_name"
                done
                echo
                echo "📁 Created data directories for all remotes"
                echo "🚀 You can now start the bot with: docker compose up -d"
                echo "💡 The bot will automatically detect all configured remotes"
            fi
        fi
        exit 0
        ;;
    *)
        echo "❌ Invalid selection"
        exit 1
        ;;
esac

# Ask for custom remote name
echo
echo "🏷️  Choose a name for your $BACKEND_NAME remote:"
echo "   This can be anything you want (e.g., 'my-drive', 'company-storage', 'personal-cloud')"
echo "   The bot will automatically detect and use whatever name you choose."
echo
read -p "Remote name: " REMOTE_NAME

# Validate remote name
if [ -z "$REMOTE_NAME" ]; then
    echo "❌ Remote name cannot be empty"
    exit 1
fi

# Remove any trailing colon if user added it
REMOTE_NAME=${REMOTE_NAME%:}

echo
echo "📂 Creating data directory for: data/$REMOTE_NAME"
mkdir -p "data/$REMOTE_NAME"

echo
echo "🔧 Starting $BACKEND_NAME configuration with remote name: '$REMOTE_NAME'"
echo "This will open an interactive setup."
echo

# Backend-specific instructions
case $backend_choice in
    1)
        echo "📋 Google Drive Setup Steps:"
        echo "1. Choose 'n' for new remote"
        echo "2. Name: $REMOTE_NAME"
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
        echo "📋 Nextcloud/WebDAV Setup Steps:"
        echo "1. Choose 'n' for new remote"
        echo "2. Name: $REMOTE_NAME"
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
        echo "2. Name: $REMOTE_NAME"
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
if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf 2>/dev/null | grep -q "$REMOTE_NAME:"; then
    echo "✅ $BACKEND_NAME remote '$REMOTE_NAME' configured successfully!"
    
    echo
    echo "🧪 Testing connection..."
    case $backend_choice in
        1|3)
            # For Google Drive and Proton Drive, test with lsd
            if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest lsd $REMOTE_NAME: --config /config/rclone.conf > /dev/null 2>&1; then
                echo "✅ Connection test successful!"
            else
                echo "⚠️  Connection test failed. Check your configuration."
            fi
            ;;
        2)
            # For Nextcloud, test with about command (more reliable)
            if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest about $REMOTE_NAME: --config /config/rclone.conf > /dev/null 2>&1; then
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
    echo "🚀 Setup completed! Your remote '$REMOTE_NAME' is ready."
    echo
    echo "📊 Available commands:"
    echo "• Start bot: docker compose up -d"
    echo "• Test connection: docker run --rm -v \$(pwd)/rclone-config:/config rclone/rclone:latest lsd $REMOTE_NAME: --config /config/rclone.conf"
    echo "• Check storage: docker run --rm -v \$(pwd)/rclone-config:/config rclone/rclone:latest about $REMOTE_NAME: --config /config/rclone.conf"
    
    echo
    echo "💡 The bot will automatically:"
    echo "• Detect your remote named '$REMOTE_NAME'"
    echo "• Create a storage option called '$BACKEND_NAME ($REMOTE_NAME)'"
    echo "• Allow users to select this backend for downloads"
    
    echo
    echo "📁 Your files will be saved to: data/$REMOTE_NAME/"
    echo "☁️  And automatically uploaded to: $REMOTE_NAME:youtube-downloads"
    
else
    echo "❌ $BACKEND_NAME remote '$REMOTE_NAME' not found!"
    echo "Please run the setup again and make sure to name the remote '$REMOTE_NAME'"
    echo "The remote name is case-sensitive and must match exactly."
fi

echo
echo "🔧 Want to configure another backend?"
echo "Run this script again to add more remotes to the same config file."
echo "Each remote can have any name you choose." 