# Training Job Cancellation - Zombie Process Fix (FINAL)

**Date**: October 26, 2025  
**Status**: ✅ **WORKING** - Tested and Verified

## Problem Summary

When users cancelled training jobs:
1. RQ marked jobs as "cancelled" in Redis
2. Database updated job status to "cancelled"
3. **BUT**: The actual Python worker process kept running at 99% CPU (zombie)
4. Worker showed "busy" and couldn't process new jobs

## Root Causes Discovered

### 1. RQ Limitation
`rq_job.cancel()` and `rq_job.kill()` only update Redis state - they **do not kill OS processes**.

### 2. PATH Issue
The `trad-api.service` systemd service only had `/srv/trad/.venv/bin` in PATH:
```
Environment=PATH=/srv/trad/.venv/bin
```

This meant subprocess commands couldn't find system binaries like:
- `/usr/bin/pgrep` ❌
- `/usr/bin/ps` ❌  
- `/usr/bin/kill` ❌
- `/usr/bin/systemctl` ❌

## Solution Implemented

Enhanced the cancel endpoint in `/workspaces/Trad/api/training_queue.py` to:

### 1. Find Training Processes (with absolute path)
```python
result = subprocess.run(
    ["/usr/bin/pgrep", "-f", "training/worker.py"],
    capture_output=True,
    text=True
)
```

### 2. Check CPU Usage (with absolute path)
```python
ps_result = subprocess.run(
    ["/usr/bin/ps", "-p", pid, "-o", "pid=,pcpu=,args="],
    capture_output=True,
    text=True
)
```

### 3. Kill High-CPU Processes (with absolute path)
```python
if cpu_usage > 50.0:
    subprocess.run(["/usr/bin/kill", "-9", pid], check=True)
    killed_process = True
```

### 4. Restart Worker Service (with absolute path)
```python
if killed_process:
    subprocess.run(["/usr/bin/systemctl", "restart", "trad-worker.service"], check=True)
```

### 5. Comprehensive Logging
- Logs all PIDs found
- Shows CPU usage for each process
- Reports which processes are killed
- Captures and logs all errors

## Test Results

**Tested**: October 26, 2025 00:34 UTC

**Logs from successful cancellation:**
```
INFO:api.training_queue:========== CANCEL ENDPOINT CALLED FOR JOB 109 ==========
INFO:api.training_queue:Cancelled RQ job efc099f7-5bff-4a32-8f84-299ac9ae3c9d
INFO:api.training_queue:===== ATTEMPTING TO KILL WORKER PROCESSES FOR JOB efc099f7-5bff-4a32-8f84-299ac9ae3c9d =====
INFO:api.training_queue:Running pgrep to find training worker processes...
INFO:api.training_queue:Found 2 training worker PIDs: ['3607678', '3607933']
INFO:api.training_queue:PID 3607678 ps output: 3607678  0.4 /srv/trad/.venv/bin/python /srv/trad/training/worker.py
INFO:api.training_queue:PID 3607678 CPU usage: 0.4%
INFO:api.training_queue:PID 3607933 ps output: 3607933 99.7 /srv/trad/.venv/bin/python /srv/trad/training/worker.py
INFO:api.training_queue:PID 3607933 CPU usage: 99.7%
INFO:api.training_queue:Killing high-CPU process PID 3607933
INFO:api.training_queue:✓ Killed training worker process PID 3607933 (CPU: 99.7%)
INFO:api.training_queue:Restarted trad-worker.service after killing process
INFO:api.training_queue:Cancelled job 109 (was running)
```

**Results:**
- ✅ Zombie process found (PID 3607933 at 99.7% CPU)
- ✅ Zombie process killed successfully
- ✅ Worker service restarted
- ✅ New jobs start immediately after cancellation

## How It Works Now

### User Clicks "Cancel" →

1. **UI calls** `DELETE /api/training/{job_id}`

2. **API endpoint**:
   - Marks job as cancelled in database
   - Cancels RQ job in Redis
   - Finds all training worker processes
   - Identifies processes with >50% CPU
   - Kills zombie processes with `kill -9`
   - Restarts worker service for clean state
   - Runs orphan cleanup

3. **Result**: Worker ready for new jobs immediately

## Files Modified

### `/workspaces/Trad/api/training_queue.py`
- Enhanced `cancel_training_job()` endpoint with OS-level process management
- All subprocess commands use absolute paths
- Comprehensive logging at each step
- Automatic worker restart after killing processes

### Created Documentation
- `/workspaces/Trad/docs/ZOMBIE_PROCESS_FIX_FINAL.md` (this file)
- `/workspaces/Trad/docs/ZOMBIE_PROCESS_FIX_V2.md` (earlier version)
- `/workspaces/Trad/ops/scripts/tail_api_logs.sh` (log monitoring script)

## Debugging Tools

### Watch logs in real-time:
```bash
bash ops/scripts/tail_api_logs.sh
```

Or directly:
```bash
ssh root@138.68.245.159 'tail -f /var/log/trad-dashboard.log'
```

### Check for zombie processes:
```bash
ssh root@138.68.245.159 'ps aux | grep "training/worker.py" | grep -v grep'
```
Should only show 1 main worker process (low CPU).

### Manual cleanup (if needed):
```bash
ssh root@138.68.245.159
ps aux | grep "training/worker.py" | grep -v grep
# Find PID with high CPU
kill -9 <PID>
systemctl restart trad-worker.service
cd /srv/trad && . .venv/bin/activate && python training/cleanup_orphaned_jobs.py
```

## Deployment

**Deployed**: October 26, 2025 00:36:08 UTC  
**Server**: 138.68.245.159  
**Services**: trad-api.service, trad-worker.service  

## Verification

After deployment:
```bash
# Check worker status
ssh root@138.68.245.159 'cd /srv/trad && . .venv/bin/activate && rq info'

# Should show:
# - Worker: idle (not busy)
# - 0 jobs executing
# - Only 1 python process for training/worker.py
```

## Known Limitations

### CPU Threshold
Currently kills processes with >50% CPU. This works for training jobs which are CPU-intensive. If training becomes I/O-bound, may need to:
- Lower threshold
- Add process age check
- Check process tree relationships

### No Timeout
Training jobs don't have a maximum runtime. Consider adding:
- Auto-cancel after X hours
- Progress timeout (no progress for Y minutes)

## Alternative Solutions Considered

### 1. Fix systemd service PATH
Add `/usr/bin` to PATH in service file:
```ini
Environment=PATH=/srv/trad/.venv/bin:/usr/bin
```
**Rejected**: Absolute paths are more explicit and safer.

### 2. Install procps package
Ensure `pgrep` is available via package manager.
**Rejected**: Tools were already installed, PATH was the issue.

### 3. Use Python's psutil
Pure Python solution without subprocess:
```python
import psutil
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
    if 'training/worker.py' in proc.cmdline():
        ...
```
**Rejected**: psutil already installed but subprocess approach is simpler for this use case.

## Success Criteria

- [x] Cancel button kills zombie processes
- [x] Worker restarts automatically
- [x] New jobs start immediately after cancellation
- [x] No manual cleanup required
- [x] Comprehensive logging for debugging
- [x] Error handling for all subprocess calls

## Future Improvements

1. **Add health check endpoint** showing:
   - Active worker PIDs
   - CPU usage per process
   - Zombie process detection
   - Last successful job completion time

2. **Add job timeout mechanism**:
   - Maximum runtime per job (e.g., 2 hours)
   - Progress timeout (no update for 10 minutes)
   - Automatic cleanup and retry

3. **Add worker monitoring dashboard**:
   - Real-time worker status
   - Process tree visualization
   - Historical job completion times
   - Failure rate metrics

4. **Improve process detection**:
   - Check parent-child relationships
   - Verify RQ job ID matches running process
   - Add process age filter

## Conclusion

The zombie process issue is **fully resolved**. The cancel function now:
- Successfully finds and kills zombie worker processes
- Restarts the worker service for clean state
- Allows new jobs to start immediately
- Provides detailed logging for debugging

**Status**: Production-ready ✅
