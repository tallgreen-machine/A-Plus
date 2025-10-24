# RQ Job Queue Architecture

## Overview

The V2 Training system uses **RQ (Redis Queue)** to handle long-running training jobs. This architecture provides:

- **Process Isolation**: Training runs in separate worker process from API
- **Resilience**: API restarts don't kill training jobs
- **Scalability**: Can add more workers to process jobs in parallel
- **Management**: Cancel, retry, and monitor jobs
- **No Orphaned Processes**: Workers are properly managed by systemd

## Architecture

```
┌──────────────────────┐         ┌──────────────────────────┐
│   FastAPI Server     │         │   Training Worker        │
│   (port 8000)        │◄───────►│   (separate process)     │
│                      │  Redis  │                          │
│  - Receive requests  │  Queue  │  - Process training jobs │
│  - Enqueue jobs      │         │  - Update progress       │
│  - Return status     │         │  - Save configurations   │
│  - Serve UI          │         │  - Handle errors         │
└──────────────────────┘         └──────────────────────────┘
         │                                    │
         └────────────────────────────────────┘
                        │
         ┌──────────────────────────────────┐
         │  PostgreSQL + Redis              │
         │  - training_jobs                 │
         │  - training_progress             │
         │  - trained_configurations        │
         │  - RQ job queue                  │
         └──────────────────────────────────┘
```

## Components

### 1. Redis

**Purpose**: Job queue storage  
**Installation**: `apt-get install redis-server`  
**Connection**: `redis://localhost:6379/0` (database 0)  
**Configuration**: Standard Redis configuration, no special setup needed

### 2. RQ Worker (`worker.py`)

**Location**: `/srv/trad/worker.py`  
**Process**: Separate Python process listening to 'training' queue  
**Management**: Systemd service (`trad-worker.service`)  
**Logs**: `/var/log/trad-worker.log`

**Main loop**:
```python
with Connection(redis_conn):
    worker = Worker(['training'], name='training-worker')
    worker.work(with_scheduler=False)  # Blocking call
```

### 3. Training Jobs (`training/rq_jobs.py`)

**Function**: `run_training_job()`  
**Purpose**: Executes training in worker process  
**Timeout**: 30 minutes  
**Result TTL**: 24 hours (success), 7 days (failure)

**Execution flow**:
1. Data Preparation (0-25%)
2. Optimization (25-75%)
3. Validation (75-95%)
4. Save Configuration (95-100%)

### 4. API Integration (`api/training_v2.py`)

**Endpoint**: `POST /api/v2/training/start`  
**Action**: Enqueues job instead of BackgroundTasks

**Before (BROKEN)**:
```python
background_tasks.add_task(run_training_task, job_id, request)
```

**After (FIXED)**:
```python
from training.rq_jobs import run_training_job

queue = get_training_queue()
rq_job = queue.enqueue(
    run_training_job,
    job_id=job_id,
    strategy=request.strategy,
    symbol=request.symbol,
    # ... other parameters
    job_timeout='30m',
    result_ttl=86400,
    failure_ttl=604800
)
```

## Deployment

### Installation Steps

1. **Install Redis**:
   ```bash
   sudo /srv/trad/ops/scripts/install_redis.sh
   ```

2. **Install Python dependencies**:
   ```bash
   cd /srv/trad
   .venv/bin/pip install redis>=5.0.0 rq>=1.15.0
   ```

3. **Install worker service**:
   ```bash
   sudo cp ops/systemd/trad-worker.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable trad-worker.service
   sudo systemctl start trad-worker.service
   ```

4. **Verify installation**:
   ```bash
   # Check Redis
   redis-cli ping  # Should return PONG
   
   # Check worker
   systemctl status trad-worker.service
   tail -f /var/log/trad-worker.log
   ```

### Automated Deployment

The deployment script (`ops/scripts/deploy_to_server.sh`) handles:
- Redis installation (if not present)
- Worker service installation
- Service startup and health checks

```bash
SERVER=138.68.245.159 SSH_USER=root ./ops/scripts/deploy_to_server.sh
```

## Operations

### Monitoring

**Check worker status**:
```bash
systemctl status trad-worker.service
```

**View worker logs**:
```bash
tail -f /var/log/trad-worker.log
```

**Check Redis queue**:
```bash
redis-cli
> LLEN rq:queue:training  # Number of queued jobs
> SMEMBERS rq:workers     # Active workers
> KEYS rq:job:*           # All jobs
```

**Monitor job progress**:
```bash
curl http://138.68.245.159:8000/api/v2/training/jobs/{job_id}/progress
```

### Managing Jobs

**Cancel a running job**:
```bash
# Via API (future implementation)
curl -X DELETE http://138.68.245.159:8000/api/v2/training/jobs/{job_id}

# Via Redis CLI
redis-cli
> DEL rq:job:{rq_job_id}
```

**Retry a failed job**:
```bash
# Via API (future implementation)
curl -X POST http://138.68.245.159:8000/api/v2/training/jobs/{job_id}/retry
```

**View queue status**:
```bash
curl http://138.68.245.159:8000/api/v2/training/queue
```

### Restarting Services

**Restart worker** (does NOT kill jobs - they continue in Redis):
```bash
sudo systemctl restart trad-worker.service
```

**Restart API** (does NOT affect jobs):
```bash
sudo systemctl restart dashboard.service
```

**Restart both** (safe, no job loss):
```bash
sudo systemctl restart trad-worker.service dashboard.service
```

### Scaling Workers

**Run multiple workers** (for parallel job processing):
```bash
# Create additional service files
sudo cp /etc/systemd/system/trad-worker.service /etc/systemd/system/trad-worker-2.service

# Edit to change worker name
sudo nano /etc/systemd/system/trad-worker-2.service
# Change: --name training-worker-2

# Start second worker
sudo systemctl daemon-reload
sudo systemctl enable trad-worker-2.service
sudo systemctl start trad-worker-2.service
```

**Note**: Currently jobs run sequentially. For parallel execution:
1. Add more workers
2. Ensure database writes are thread-safe
3. Monitor resource usage (CPU, memory)

## Troubleshooting

### Worker not starting

**Check logs**:
```bash
journalctl -u trad-worker.service -f
cat /var/log/trad-worker.log
```

**Common issues**:
- Redis not running: `sudo systemctl start redis-server`
- Virtual environment missing: Check `/srv/trad/.venv`
- Permissions: `sudo chown -R root:root /srv/trad`

### Jobs stuck in PENDING

**Symptoms**: Job submitted but never starts

**Diagnosis**:
```bash
# Check worker is running
systemctl status trad-worker.service

# Check Redis connection
redis-cli ping

# Check queue length
redis-cli LLEN rq:queue:training
```

**Fix**:
```bash
# Restart worker
sudo systemctl restart trad-worker.service

# Clear stuck jobs (if needed)
redis-cli FLUSHDB  # WARNING: Deletes all jobs
```

### Jobs failing immediately

**Symptoms**: Job moves to FAILED status quickly

**Diagnosis**:
```bash
# Check worker logs for errors
tail -n 100 /var/log/trad-worker.log

# Check job result in Redis
redis-cli
> GET rq:job:{rq_job_id}
```

**Common issues**:
- Import errors: Missing dependencies
- Database connection: Check /etc/trad/trad.env
- Data unavailable: Exchange API issues

### Memory issues

**Symptoms**: Worker crashes, OOM errors

**Diagnosis**:
```bash
# Check memory usage
free -h
ps aux | grep python | grep worker

# Check Redis memory
redis-cli INFO memory
```

**Fix**:
- Reduce n_iterations in training requests
- Add swap space
- Limit concurrent workers
- Increase server RAM

## Performance

### Job Timing

**Typical training job**:
- Data preparation: 10-30 seconds
- Optimization (200 iterations): 3-8 minutes
- Validation: 1-3 minutes
- Save configuration: 5-10 seconds
- **Total**: 5-12 minutes

### Resource Usage

**Per worker**:
- CPU: 1-2 cores (optimization-bound)
- Memory: 500MB-1GB (data + models)
- Disk: Minimal (PostgreSQL handles writes)

**Redis**:
- Memory: ~50MB baseline + job data
- CPU: Negligible
- Disk: Persistence can be disabled for job queue

## Security

### Redis Access

**Default**: Bound to localhost only (safe)  
**Configuration**: `/etc/redis/redis.conf`

```
bind 127.0.0.1 ::1
protected-mode yes
requirepass <strong-password>  # Optional
```

### Environment Variables

**Sensitive data in**: `/etc/trad/trad.env`  
**Permissions**: `chmod 600 /etc/trad/trad.env`

```bash
DB_PASSWORD=TRAD123!
REDIS_URL=redis://localhost:6379/0
```

### Worker Isolation

- Runs as `root` (systemd User= setting)
- No network exposure (internal process)
- Reads environment from `/etc/trad/trad.env`

## Future Enhancements

### RQ Dashboard

**Optional monitoring UI**:
```bash
pip install rq-dashboard
rq-dashboard --redis-url redis://localhost:6379/0 --port 9181
```

**Access**: http://138.68.245.159:9181

### Job Prioritization

```python
# High priority jobs
queue.enqueue(run_training_job, ..., job_priority='high')

# Low priority jobs
queue.enqueue(run_training_job, ..., job_priority='low')
```

### Scheduled Training

```python
from rq_scheduler import Scheduler

scheduler = Scheduler('training', connection=redis_conn)
scheduler.cron(
    '0 2 * * *',  # Every day at 2 AM
    func=run_training_job,
    kwargs={'strategy': 'LIQUIDITY_SWEEP', ...}
)
```

### Result Caching

Store optimization results in Redis for quick retrieval:
```python
redis_conn.setex(
    f'training:result:{config_id}',
    86400,  # 24 hour TTL
    json.dumps(result)
)
```

## References

- **RQ Documentation**: https://python-rq.org/
- **Redis Documentation**: https://redis.io/documentation
- **Systemd Service Management**: `man systemctl`
- **V2 Training Schema**: See `docs/V2_TRAINING_SCHEMA_MAPPING.md`
