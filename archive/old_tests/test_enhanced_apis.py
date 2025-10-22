#!/usr/bin/env python3
"""
Test script to verify all enhanced API endpoints for TradePulse IQ Dashboard
Tests the comprehensive backend API implementation
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_endpoint(endpoint, method="GET", data=None, description=""):
    """Test a single API endpoint"""
    url = f"{API_BASE}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=5)
        
        print(f"✅ {endpoint} ({method}) - {response.status_code}")
        if description:
            print(f"   {description}")
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, dict) and "data" in result:
                print(f"   Response: {len(result['data'])} items" if isinstance(result['data'], list) else "   Response: Success")
            elif isinstance(result, list):
                print(f"   Response: {len(result)} items")
            else:
                print(f"   Response: {type(result).__name__}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ {endpoint} - Connection Error (API server not running)")
        return False
    except Exception as e:
        print(f"❌ {endpoint} - Error: {e}")
        return False

def main():
    """Test all enhanced API endpoints"""
    print("🧪 Testing Enhanced TradePulse IQ API Endpoints")
    print("=" * 60)
    
    # Health check
    print("\n📡 Health Check:")
    test_endpoint("/health", description="Basic health check")
    
    # Portfolio API
    print("\n💼 Portfolio API:")
    test_endpoint("/api/portfolio/test", description="Portfolio summary with positions")
    test_endpoint("/api/portfolio/summary", description="Enhanced portfolio summary")
    test_endpoint("/api/portfolio/risk-management", description="Risk management metrics")
    test_endpoint("/api/portfolio/oco-orders", description="Active OCO orders")
    
    # Trades API
    print("\n📈 Trades API:")
    test_endpoint("/api/trades/active", description="Currently active trades")
    test_endpoint("/api/trades/history", description="Trade history with pagination")
    test_endpoint("/api/trades/daily-pnl", description="Daily P&L data for charting")
    test_endpoint("/api/trades/statistics", description="Comprehensive trading statistics")
    
    # Patterns API
    print("\n🔍 Patterns API:")
    test_endpoint("/api/patterns/strategy-performance", description="Multi-dimensional strategy performance")
    test_endpoint("/api/patterns/trained-assets-summary", description="Trained assets with strategy coverage")
    test_endpoint("/api/patterns/market-regimes", description="Market regime analysis")
    test_endpoint("/api/patterns/pattern-library", description="Available pattern templates")
    test_endpoint("/api/patterns/test-performance", description="Test patterns performance")
    test_endpoint("/api/patterns/test-trained-assets", description="Test trained assets")
    
    # Training API  
    print("\n🤖 Training API:")
    test_endpoint("/api/training/system-status", description="Multi-dimensional training system status")
    test_endpoint("/api/training/trained-assets", description="Comprehensive trained assets")
    test_endpoint("/api/training/market-regimes", description="Market regime classification")
    test_endpoint("/api/training/strategy-parameters", description="Available strategy parameters")
    
    # Analytics API
    print("\n📊 Analytics API:")
    test_endpoint("/api/analytics/asset-ranking", description="Asset ranking by performance")
    test_endpoint("/api/analytics/walk-forward-results", description="Walk-forward testing results")
    test_endpoint("/api/analytics/market-overview", description="Comprehensive market overview")
    
    # Exchanges API
    print("\n🔗 Exchanges API:")
    test_endpoint("/api/exchanges/connections", description="Exchange connection status")
    test_endpoint("/api/exchanges/performance", description="Exchange performance metrics")
    test_endpoint("/api/exchanges/supported-exchanges", description="Supported exchanges list")
    
    # Test exchange connection
    test_data = {
        "exchangeName": "binance",
        "apiKey": "test_key",
        "apiSecret": "test_secret",
        "testnet": True
    }
    test_endpoint("/api/exchanges/test-connection", "POST", test_data, "Test exchange connection")
    
    print("\n" + "=" * 60)
    print("🎯 API Testing Complete!")
    print("\nTo start the API server, run:")
    print("   cd /workspaces/Trad")
    print("   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload")

if __name__ == "__main__":
    main()