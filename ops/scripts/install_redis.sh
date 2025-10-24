#!/bin/bash
#
# Install and configure Redis on Ubuntu
#
# Usage: sudo ./install_redis.sh
#

set -e

echo "🔧 Installing Redis..."

# Update package index
apt-get update

# Install Redis
apt-get install -y redis-server

# Configure Redis to start on boot
systemctl enable redis-server

# Start Redis
systemctl start redis-server

# Test connection
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis installed and running"
    redis-cli --version
else
    echo "❌ Redis installation failed"
    exit 1
fi

# Show Redis status
systemctl status redis-server --no-pager

echo ""
echo "Redis is now running on localhost:6379"
echo "Connection URL: redis://localhost:6379/0"
