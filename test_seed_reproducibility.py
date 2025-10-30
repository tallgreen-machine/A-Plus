#!/usr/bin/env python3
"""
Test script to verify training reproducibility with seed parameter.

Tests:
1. Submit two jobs with same seed (42) - should explore identical parameters
2. Submit job with different seed (123) - should explore different parameters
3. Verify logs show seed values
"""
import requests
import time
import json
from datetime import datetime

API_BASE = "http://138.68.245.159:8000/api/training"

def submit_training_job(seed: int, test_name: str):
    """Submit a test training job with specified seed"""
    payload = {
        "strategy_name": "test_strategy",
        "exchange": "binanceus",
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "regime": "bull",
        "lookback_candles": 10000,  # Use 10k candles (known to work with existing data)
        "optimizer": "bayesian",
        "n_iterations": 10,  # Small for quick test
        "seed": seed
    }
    
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"Submitting job with seed={seed}")
    print(f"{'='*60}")
    
    response = requests.post(f"{API_BASE}/submit", json=payload)
    
    if response.status_code == 200:
        job_data = response.json()
        job_id = job_data.get('job_id') or job_data.get('id')
        print(f"✓ Job submitted successfully: {job_id}")
        return job_id
    else:
        print(f"✗ Failed to submit job: {response.status_code}")
        print(f"  Error: {response.text}")
        return None

def get_job_status(job_id: str):
    """Get status of a training job"""
    response = requests.get(f"{API_BASE}/jobs/{job_id}")
    if response.status_code == 200:
        return response.json()
    return None

def wait_for_job_completion(job_id: str, timeout: int = 600):
    """Wait for job to complete and return final status"""
    print(f"Waiting for job {job_id} to complete...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        job_status = get_job_status(job_id)
        if not job_status:
            print(f"  ✗ Could not fetch job status")
            return None
        
        status = job_status.get('status')
        print(f"  Status: {status}")
        
        if status in ('completed', 'failed', 'cancelled'):
            print(f"  ✓ Job finished with status: {status}")
            return job_status
        
        time.sleep(5)
    
    print(f"  ✗ Timeout after {timeout}s")
    return None

def get_job_details(job_id: str):
    """Get detailed job information including seed and results"""
    response = requests.get(f"{API_BASE}/jobs/{job_id}/details")
    if response.status_code == 200:
        return response.json()
    return None

def extract_explored_params(job_details):
    """Extract the parameters that were explored during optimization"""
    if not job_details:
        return None
    
    # Try to get optimization history from result
    result = job_details.get('result', {})
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except:
            pass
    
    # Different optimizers may store history differently
    history = None
    if isinstance(result, dict):
        history = result.get('optimization_history') or result.get('history')
    
    return history

def main():
    """Run reproducibility tests"""
    print("\n" + "="*60)
    print("TRAINING REPRODUCIBILITY TEST")
    print("Testing seed parameter for deterministic training")
    print("="*60)
    
    # Test 1: Submit job with seed=42 (first run)
    job1_id = submit_training_job(seed=42, test_name="First run with seed=42")
    if not job1_id:
        print("\n✗ Test failed: Could not submit first job")
        return
    
    time.sleep(2)
    
    # Test 2: Submit job with seed=42 (second run, should be identical)
    job2_id = submit_training_job(seed=42, test_name="Second run with seed=42 (should match first)")
    if not job2_id:
        print("\n✗ Test failed: Could not submit second job")
        return
    
    time.sleep(2)
    
    # Test 3: Submit job with seed=123 (different seed, should be different)
    job3_id = submit_training_job(seed=123, test_name="Run with seed=123 (should differ)")
    if not job3_id:
        print("\n✗ Test failed: Could not submit third job")
        return
    
    print("\n" + "="*60)
    print("All jobs submitted successfully!")
    print("="*60)
    print(f"Job 1 (seed=42):  {job1_id}")
    print(f"Job 2 (seed=42):  {job2_id}")
    print(f"Job 3 (seed=123): {job3_id}")
    print("\nTo monitor progress:")
    print(f"  curl {API_BASE}/jobs/{job1_id}")
    print(f"  curl {API_BASE}/jobs/{job2_id}")
    print(f"  curl {API_BASE}/jobs/{job3_id}")
    print("\nTo view logs on server:")
    print(f"  ssh root@138.68.245.159 'journalctl -u trad-worker.service -f'")
    print("\nNOTE: Jobs will be queued and run sequentially by the RQ worker.")
    print("This test script has submitted the jobs but does not wait for completion.")
    print("Check job status using the curl commands above or view the dashboard.")
    
    # Save job IDs for reference
    with open('/workspaces/Trad/test_seed_reproducibility_jobs.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'jobs': {
                'job1_seed42_run1': job1_id,
                'job2_seed42_run2': job2_id,
                'job3_seed123': job3_id
            }
        }, f, indent=2)
    
    print("\n✓ Job IDs saved to: test_seed_reproducibility_jobs.json")

if __name__ == "__main__":
    main()
