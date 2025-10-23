"""
Test Progress Tracking API

Demonstrates real-time progress reporting for training jobs.
This script shows what the Strategy Studio UI will poll to display progress.
"""

import asyncio
import aiohttp
import json
from datetime import datetime


async def monitor_training_progress(base_url: str, job_id: str, poll_interval: float = 2.0):
    """
    Monitor training progress by polling the progress endpoint.
    
    This simulates what the Strategy Studio UI will do.
    """
    print("=" * 80)
    print("TRAINING PROGRESS MONITOR")
    print("=" * 80)
    print(f"Base URL: {base_url}")
    print(f"Job ID: {job_id}")
    print(f"Poll interval: {poll_interval}s")
    print()
    
    url = f"{base_url}/api/v2/training/jobs/{job_id}/progress"
    
    async with aiohttp.ClientSession() as session:
        previous_step = None
        previous_iteration = None
        
        while True:
            try:
                async with session.get(url) as response:
                    if response.status == 404:
                        print(f"❌ Job {job_id} not found")
                        break
                    
                    if response.status != 200:
                        print(f"⚠️  Error {response.status}: {await response.text()}")
                        await asyncio.sleep(poll_interval)
                        continue
                    
                    data = await response.json()
                    
                    # Extract key fields
                    percentage = data.get('percentage', 0.0)
                    current_step = data.get('current_step', 'Unknown')
                    step_number = data.get('step_number', 0)
                    total_steps = data.get('total_steps', 4)
                    step_percentage = data.get('step_percentage', 0.0)
                    is_complete = data.get('is_complete', False)
                    error_message = data.get('error_message')
                    
                    # Optimizer-specific
                    current_iteration = data.get('current_iteration')
                    total_iterations = data.get('total_iterations')
                    best_score = data.get('best_score')
                    current_score = data.get('current_score')
                    
                    # ETA
                    eta = data.get('estimated_completion')
                    
                    # Print update if step changed or significant progress
                    if current_step != previous_step or (current_iteration and current_iteration != previous_iteration):
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Step {step_number}/{total_steps}: {current_step}")
                        print(f"  Overall: {percentage:.1f}%  |  Step: {step_percentage:.1f}%")
                        
                        if current_iteration and total_iterations:
                            print(f"  Iteration: {current_iteration}/{total_iterations}")
                        
                        if best_score is not None:
                            print(f"  Best Score: {best_score:.4f}")
                        
                        if current_score is not None:
                            print(f"  Current Score: {current_score:.4f}")
                        
                        if eta:
                            print(f"  ETA: {eta}")
                        
                        # Progress bar
                        bar_width = 50
                        filled = int(bar_width * percentage / 100)
                        bar = '█' * filled + '░' * (bar_width - filled)
                        print(f"  [{bar}] {percentage:.1f}%")
                    
                    previous_step = current_step
                    previous_iteration = current_iteration
                    
                    # Check completion
                    if is_complete:
                        if error_message:
                            print(f"\n❌ Training FAILED")
                            print(f"   Error: {error_message}")
                        else:
                            print(f"\n✅ Training COMPLETE!")
                            print(f"   Final Score: {best_score:.4f if best_score else 'N/A'}")
                        break
                    
                    # Wait before next poll
                    await asyncio.sleep(poll_interval)
                    
            except KeyboardInterrupt:
                print("\n\n⏸️  Monitoring stopped by user")
                break
            except Exception as e:
                print(f"⚠️  Error: {e}")
                await asyncio.sleep(poll_interval)


async def start_training_and_monitor(base_url: str):
    """
    Start a training job and monitor its progress.
    """
    print("Starting new training job...")
    print()
    
    # Training request
    training_request = {
        "strategy": "LIQUIDITY_SWEEP",
        "symbol": "BTC/USDT",
        "exchange": "binanceus",
        "timeframe": "5m",
        "optimizer": "bayesian",
        "lookback_days": 30,
        "n_iterations": 20,  # Smaller for quick test
        "run_validation": False
    }
    
    # Start training job
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/v2/training/start",
            json=training_request
        ) as response:
            if response.status != 200:
                print(f"❌ Failed to start training: {await response.text()}")
                return
            
            result = await response.json()
            job_id = result['job_id']
            
            print(f"✅ Training job started!")
            print(f"   Job ID: {job_id}")
            print()
    
    # Monitor progress
    await monitor_training_progress(base_url, job_id, poll_interval=3.0)


if __name__ == "__main__":
    import sys
    
    # Usage: python test_progress_tracking.py [job_id]
    # If job_id provided, monitor existing job
    # Otherwise, start new job and monitor
    
    BASE_URL = "http://138.68.245.159:8000"
    
    if len(sys.argv) > 1:
        # Monitor existing job
        job_id = sys.argv[1]
        asyncio.run(monitor_training_progress(BASE_URL, job_id, poll_interval=2.0))
    else:
        # Start new job and monitor
        asyncio.run(start_training_and_monitor(BASE_URL))
