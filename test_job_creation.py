#!/usr/bin/env python3
"""Test job creation and progress tracking"""
import asyncio
import sys
import requests
import time

API_URL = "http://localhost:8000/api/training"

async def test_job_creation():
    """Create a training job and monitor its progress"""
    
    # Create job
    print("Creating training job...")
    response = requests.post(
        f"{API_URL}/start",
        json={
            "strategy": "LIQUIDITY_SWEEP",
            "symbol": "BTC/USDT",
            "exchange": "binanceus",
            "timeframe": "5m",
            "regime": "sideways",
            "optimizer": "random",
            "lookback_days": 10000,
            "n_iterations": 5,  # Small number for quick test
            "run_validation": True,
            "data_filter_config": {
                "enable_filtering": True,
                "min_volume_threshold": 0.1
            }
        }
    )
    
    if response.status_code != 200:
        print(f"Error creating job: {response.status_code}")
        print(response.text)
        return
    
    job_data = response.json()
    job_id = job_data.get('job_id')
    print(f"✅ Job created: {job_id}")
    print(f"   Status: {job_data.get('status')}")
    
    # Monitor progress
    print("\nMonitoring progress (30 seconds)...")
    for i in range(30):
        time.sleep(1)
        
        # Get job status
        status_response = requests.get(f"{API_URL}/jobs/{job_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get('status')
            progress = status_data.get('progress', 0)
            episode = status_data.get('current_episode')
            total = status_data.get('total_episodes')
            
            episode_str = f"{episode}/{total}" if episode and total else "N/A"
            print(f"[{i+1}s] Status: {status:10s} Progress: {progress:6.2f}% Episodes: {episode_str}")
            
            if status in ['COMPLETED', 'FAILED', 'ERROR']:
                print(f"\n✅ Job finished with status: {status}")
                break
    else:
        print("\n⏱️ Timeout reached")

if __name__ == "__main__":
    asyncio.run(test_job_creation())
