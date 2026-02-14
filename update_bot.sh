#!/bin/bash

# Update script for VPS
# Run this to pull changes and restart the bot

echo "⬇️ Pulling latest changes..."
git pull

if [ $? -ne 0 ]; then
    echo "❌ Git pull failed."
    exit 1
fi

echo "🔄 Restarting bot service..."
# Assuming you used the systemd service name 'vps_bot'
sudo systemctl restart vps_bot

echo "✅ Update complete!"
