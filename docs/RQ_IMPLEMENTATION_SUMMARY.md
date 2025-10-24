# RQ Implementation Summary

## What Changed

We replaced FastAPI BackgroundTasks with RQ (Redis Queue) for training job execution. This solves the critical architectural flaw where long-running training jobs in the API process caused orphaned processes and crash-loops.

## Files Created

### 1. `worker.py` (89 lines)
RQ worker process that runs training jobs.
- Connects to Redis on startup
- Listens to 'training' queue
- Processes jobs via `worker.work()` (blocking call)
- Managed by systemd

### 2. `ops/systemd/trad-worker.service` (28 lines)
Systemd unit for worker process.
- Depends on redis.service
- Runs `/srv/trad/.venv/bin/python /srv/trad/worker.py`
- Auto-restart on failure
- Logs to `/var/log/trad-worker.log`

### 3. `training/rq_jobs.py` (174 lines)
Training job definitions for RQ.
- `run_training_job()`: Main training function
- Runs in worker process (not API)
- Same logic as old `run_training_task` but refactored for RQ
- Uses sync methods (no async/await)

### 4. `ops/scripts/install_redis.sh` (29 lines)
Redis installation script.
- Installs redis-server package
- Enables and starts service
- Tests connection with `redis-cli ping`

### 5. `docs/RQ_JOB_QUEUE_ARCHITECTURE.md` (445 lines)
Complete documentation covering:
- Architecture overview
- Component details
- Deployment instructions
- Operations and monitoring
- Troubleshooting guide
- Performance characteristics
- Security considerations
- Future enhancements

## Files Modified

### 1. `api/training_v2.py`
**Before**: Used `BackgroundTasks.add_task()` to run training
**After**: Uses `queue.enqueue()` to submit job to Redis

Key changes:
- Added imports: `from redis import Redis`, `from rq import Queue`
- Added functions: `get_redis_url()`, `get_redis_connection()`, `get_training_queue()`
- Modified `/start` endpoint:
  - Removed `BackgroundTasks` parameter
  - Added `queue.enqueue(run_training_job, ...)` call
  - Set timeout (30m), result TTL (24h), failure TTL (7d)

### 2. `requirements.txt`
Added dependencies:
```
redis>=5.0.0
rq>=1.15.0
```

### 3. `config/trad.env`
Added Redis configuration:
```
REDIS_URL=redis://localhost:6379/0
```

### 4. `ops/scripts/deploy_to_server.sh`
Added deployment steps:
1. Install Redis (if not present)
2. Enable and start redis-server
3. Install trad-worker.service
4. Enable and start worker

## How It Works

### Old Architecture (BROKEN)
```
API Process (uvicorn)
├── Web requests (FastAPI)
└── Background tasks (training jobs)  ← 5-10 minutes
    ↓
    When API restarts:
    - Background tasks become orphaned
    - Hold database connections
    - Occupy port 8000
    - Cause crash-loops
```

### New Architecture (FIXED)
```
API Process                 Worker Process
├── Web requests           ├── Listen to Redis queue
└── Enqueue jobs           └── Execute training jobs
    ↓ Redis                     ↓
    [Queue]                     [Running]
    
When API restarts:
✓ Jobs stay in Redis queue
✓ Worker continues processing
✓ No orphaned processes
✓ No port conflicts
```

## Deployment Steps

### 1. Deploy Code
```bash
SERVER=138.68.245.159 SSH_USER=root ./ops/scripts/deploy_to_server.sh
```

This automatically:
- Syncs code to server
- Installs Redis (if needed)
- Installs Python dependencies (redis, rq)
- Installs worker service
- Starts worker and API

### 2. Verify Installation

**Check Redis**:
```bash
ssh root@138.68.245.159 "redis-cli ping"
# Should return: PONG
```

**Check worker**:
```bash
ssh root@138.68.245.159 "systemctl status trad-worker.service"
# Should show: active (running)
```

**Check API**:
```bash
ssh root@138.68.245.159 "systemctl status dashboard.service"
# Should show: active (running)
```

### 3. Test Training Job

**Submit job via UI**:
1. Open: http://138.68.245.159:3000
2. Navigate to Strategy Studio
3. Select strategy: Liquidity Sweep
4. Configure parameters
5. Click "Start Training"

**Monitor progress**:
```bash
# Watch worker log
ssh root@138.68.245.159 "tail -f /var/log/trad-worker.log"

# Should see:
# "Starting training job {uuid}: LIQUIDITY_SWEEP BTC/USDT..."
# "Data prepared: 2500 candles"
# "Optimization complete: best_score=1.234"
# "Training job {uuid} completed successfully"
```

**Check result**:
```bash
# Via API
curl http://138.68.245.159:8000/api/v2/training/jobs/{job_id}

# Via database
ssh root@138.68.245.159
psql -U traduser -d trad -c "SELECT config_id, strategy_name, net_profit, sharpe_ratio FROM trained_configurations ORDER BY created_at DESC LIMIT 5;"
```

### 4. Test Resilience

**Test API restart doesn't kill jobs**:
```bash
# Start a long training (200 iterations)
curl -X POST http://138.68.245.159:8000/api/v2/training/start \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "LIQUIDITY_SWEEP",
    "symbol": "BTC/USDT",
    "exchange": "binanceus",
    "timeframe": "5m",
    "optimizer": "bayesian",
    "lookback_days": 90,
    "n_iterations": 200,
    "run_validation": true
  }'

# Get job_id from response
JOB_ID="..."

# Restart API while training runs
ssh root@138.68.245.159 "sudo systemctl restart dashboard.service"

# Check job still progressing (not failed)
curl http://138.68.245.159:8000/api/v2/training/jobs/$JOB_ID/progress
# Should show: status="RUNNING", progress increasing
```

**Test no orphaned processes**:
```bash
# Before fix: Multiple uvicorn processes
ssh root@138.68.245.159 "ps aux | grep uvicorn"
# Would show 2-3 processes

# After fix: Only one uvicorn process
ssh root@138.68.245.159 "ps aux | grep uvicorn"
# Should show 1 process
```

## Expected Results

### Success Criteria
- ✓ Training job starts and completes
- ✓ Progress updates every 2 seconds
- ✓ Configuration saved to `trained_configurations`
- ✓ API restart doesn't kill jobs
- ✓ No orphaned processes after restart
- ✓ Worker log shows job execution
- ✓ Multiple jobs queue properly (sequential)

### Performance
- Data prep: 10-30 seconds
- Optimization (200 iterations): 3-8 minutes
- Validation: 1-3 minutes
- Save: 5-10 seconds
- **Total**: 5-12 minutes per job

### Resource Usage
**Worker**:
- CPU: 1-2 cores
- Memory: 500MB-1GB
- Disk: Minimal

**Redis**:
- Memory: ~50MB
- CPU: Negligible

## Rollback Plan

If RQ implementation has issues:

### 1. Stop worker
```bash
ssh root@138.68.245.159 "sudo systemctl stop trad-worker.service"
```

### 2. Revert code
```bash
git revert HEAD
SERVER=138.68.245.159 SSH_USER=root ./ops/scripts/deploy_to_server.sh
```

### 3. Remove Redis (optional)
```bash
ssh root@138.68.245.159 "sudo systemctl stop redis-server && sudo apt-get remove redis-server"
```

## Next Steps After Deployment

### Phase 1: Core Functionality (IMMEDIATE)
1. Deploy to server
2. Test end-to-end training
3. Verify resilience (API restart test)
4. Monitor for 24 hours

### Phase 2: Job Management (WEEK 1)
1. Implement `DELETE /jobs/{id}` - Cancel job
2. Implement `POST /jobs/{id}/retry` - Retry failed job
3. Implement `GET /queue` - Queue status
4. Implement `GET /workers` - Worker status

### Phase 3: Monitoring (WEEK 2)
1. Install RQ dashboard (optional UI)
2. Add Prometheus metrics
3. Set up alerts (long queue, worker down)
4. Create runbook for common issues

### Phase 4: Optimization (MONTH 1)
1. Add job prioritization (high/low priority)
2. Implement result caching
3. Add scheduled training (cron jobs)
4. Scale to multiple workers

### Phase 5: UI Improvements (MONTH 1)
1. Fix state persistence (localStorage)
2. Add job history view
3. Add queue visualization
4. Add retry/cancel buttons

## Known Issues

### 1. Import errors (EXPECTED)
```
ImportError: No module named 'redis'
ImportError: No module named 'rq'
```

**Cause**: Dependencies not installed yet  
**Fix**: Happens automatically during deployment  
**Manual fix**: `ssh root@138.68.245.159 "cd /srv/trad && .venv/bin/pip install redis rq"`

### 2. Redis connection failed
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Cause**: Redis not installed or not running  
**Fix**: `ssh root@138.68.245.159 "sudo systemctl start redis-server"`  
**Check**: `ssh root@138.68.245.159 "redis-cli ping"` (should return PONG)

### 3. Worker not picking up jobs
```
Job submitted but stays PENDING forever
```

**Cause**: Worker not running or queue misconfigured  
**Check**: `ssh root@138.68.245.159 "systemctl status trad-worker.service"`  
**Fix**: `ssh root@138.68.245.159 "sudo systemctl restart trad-worker.service"`

## Documentation

All details documented in:
- `docs/RQ_JOB_QUEUE_ARCHITECTURE.md` - Complete architecture guide
- `docs/V2_TRAINING_SCHEMA_MAPPING.md` - Database schema (existing)
- `README.md` - Project overview (may need update)

## Summary

**Problem**: FastAPI BackgroundTasks caused orphaned processes, crash-loops, lost jobs  
**Solution**: RQ job queue with separate worker process  
**Impact**: Production-grade training system with proper isolation  
**Status**: Ready to deploy  
**Next**: Run deployment script and test
