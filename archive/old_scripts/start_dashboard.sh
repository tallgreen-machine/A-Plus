#!/bin/bash

# TradePulse IQ Dashboard Startup Script
# Builds React frontend and starts FastAPI backend

set -e

echo "🚀 Starting TradePulse IQ Dashboard..."

# Set up Python environment
echo "📦 Setting up Python environment..."
cd /workspaces/Trad

# Install API dependencies if needed
if [ ! -d "api/.venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv api/.venv
fi

source api/.venv/bin/activate
pip install -r api/requirements.txt

# Build React frontend
echo "🏗️  Building React frontend..."
cd tradepulse-iq-dashboard
npm install
npm run build
cd ..

# Copy built files to API static directory
echo "📂 Setting up static files..."
if [ -d "api/static" ]; then
    rm -rf api/static
fi
mkdir -p api/static
cp -r tradepulse-iq-dashboard/dist/* api/static/

# Update API to serve from correct static directory
echo "⚙️  Configuring API server..."

# Start FastAPI server
echo "🌐 Starting FastAPI server..."
cd api
export PYTHONPATH=/workspaces/Trad:$PYTHONPATH
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload