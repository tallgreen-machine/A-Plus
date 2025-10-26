#!/bin/bash
# Tail the FastAPI service logs
# Usage: bash ops/scripts/tail_api_logs.sh

SERVER=${SERVER:-138.68.245.159}
SSH_USER=${SSH_USER:-root}

echo "Tailing trad-api.service logs on $SERVER..."
echo "Press Ctrl+C to stop"
echo ""

ssh ${SSH_USER}@${SERVER} 'journalctl -u trad-api.service -f --since "1 minute ago"'
