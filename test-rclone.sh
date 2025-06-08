#!/bin/bash

echo "🧪 rclone Multi-Backend Test"
echo "============================"
echo

# Check if config exists
if [ ! -f "rclone-config/rclone.conf" ]; then
    echo "❌ No rclone configuration found!"
    echo "Run ./setup-rclone.sh first to configure backends."
    exit 1
fi

echo "📋 Available remotes:"
REMOTES=$(docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest listremotes --config /config/rclone.conf)
echo "$REMOTES"

if [ -z "$REMOTES" ]; then
    echo "❌ No remotes configured!"
    exit 1
fi

echo
echo "🔧 Testing each backend..."
echo

# Test each remote
for remote in $REMOTES; do
    # Remove the colon from remote name
    remote_name=${remote%:}
    echo "🧪 Testing $remote_name..."
    
    # Test connection based on backend type
    case $remote_name in
        gdrive|proton)
            # Test with lsd (list directories)
            if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest lsd $remote --config /config/rclone.conf > /dev/null 2>&1; then
                echo "✅ $remote_name: Connection successful"
                
                # Get storage info
                echo "📊 $remote_name storage info:"
                docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest about $remote --config /config/rclone.conf 2>/dev/null | head -5
            else
                echo "❌ $remote_name: Connection failed"
            fi
            ;;
        nextcloud)
            # Test with about command (more reliable for WebDAV)
            if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest about $remote --config /config/rclone.conf > /dev/null 2>&1; then
                echo "✅ $remote_name: Connection successful"
                
                # Get storage info
                echo "📊 $remote_name storage info:"
                docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest about $remote --config /config/rclone.conf 2>/dev/null | head -5
            else
                echo "❌ $remote_name: Connection failed"
                echo "💡 Common Nextcloud issues:"
                echo "   - Check WebDAV URL format"
                echo "   - Verify username/password"
                echo "   - App passwords may be required"
            fi
            ;;
        *)
            # Generic test for other backends
            if docker run --rm -v $(pwd)/rclone-config:/config rclone/rclone:latest about $remote --config /config/rclone.conf > /dev/null 2>&1; then
                echo "✅ $remote_name: Connection successful"
            else
                echo "❌ $remote_name: Connection failed"
            fi
            ;;
    esac
    echo
done

echo "🚀 Available Docker Compose profiles:"
for remote in $REMOTES; do
    remote_name=${remote%:}
    echo "• $remote_name: docker compose --profile $remote_name up -d"
done

echo
echo "📁 Directory structure:"
echo "data/"
for remote in $REMOTES; do
    remote_name=${remote%:}
    if [ -d "data/$remote_name" ]; then
        file_count=$(find "data/$remote_name" -type f 2>/dev/null | wc -l)
        echo "├── $remote_name/ ($file_count files)"
    else
        echo "├── $remote_name/ (directory missing - will be created)"
    fi
done

echo
echo "🔧 Test upload to specific backend:"
echo "Example: echo 'test' > data/gdrive/test.txt"
echo "Then check: docker logs rclone-gdrive" 