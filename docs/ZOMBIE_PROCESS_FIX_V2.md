# Training Job Cancellation - Zombie Process Fix v2

**Date**: October 26, 2025  
**Status**: ✅ Enhanced and Deployed

## Problem

When users cancel training jobs, zombie worker processes remain running at ~99% CPU, preventing new jobs from starting. The worker shows "busy" but doesn't process queued jobs.

### Root Cause

The RQ library's `job.cancel()` and `job.kill()` methods only update Redis state - they **do not terminate OS processes**. This leaves child Python processes running after cancellation.

## Solution - Enhanced Cancel Function

The cancel endpoint in `/workspaces/Trad/api/training_queue.py` has been enhanced with:

### 1. OS-Level Process Management
```python
# Find all training worker processes
result = subprocess.run(["pgrep", "-f", "training/worker.py"], ...)

# Check each process
for pid in pids:
    ps_result = subprocess.run(["ps", "-p", pid, "-o", "ppid=,pcpu=,args="], ...)
    
    # Parse CPU usage
    if cpu_usage > 50.0:
        # Kill zombie process
        subprocess.run(["kill", "-9", pid])
        killed_process = True
```

### 2. Worker Service Restart
```python
# Restart worker for clean state
if killed_process:
    subprocess.run(["systemctl", "restart", "trad-worker.service"], ...)
```

### 3. Comprehensive Logging
- Logs all PIDs found
- Logs CPU usage for each process
- Logs which processes are killed
- Logs any errors during process management
- Uses `log.info()` for visibility

## Testing the Fix

### Before Testing
1. Start a new training job from the UI
2. Let it reach 10-20% progress
3. Click the Cancel button

### Viewing Logs
Use the new log tail script to watch what happens:
```bash
bash ops/scripts/tail_api_logs.sh
```

### Expected Behavior
You should see logs like:
```
INFO: Found 2 training worker PIDs: ['3600180', '3600234']
INFO: PID 3600180 ps output: 1 0.4 /srv/trad/.venv/bin/python /srv/trad/training/worker.py
INFO: PID 3600180 CPU usage: 0.4%
INFO: PID 3600234 ps output: 3600180 99.1 /srv/trad/.venv/bin/python /srv/trad/training/worker.py
INFO: PID 3600234 CPU usage: 99.1%
INFO: ✓ Killed training worker process PID 3600234 (CPU: 99.1%)
INFO: Restarted trad-worker.service after killing process
```

### Verify Success
After cancelling:
1. New job should start immediately (no stuck state)
2. Worker should show "idle" in `rq info`
3. No zombie processes: `ps aux | grep training | grep -v grep` should show only 1 main worker

## What Changed

### Files Modified
1. `/workspaces/Trad/api/training_queue.py`:
   - Added comprehensive logging at each step
   - Added error handling with specific exception types
   - Added automatic worker restart after killing process
   - Enhanced process discovery and CPU checking logic

### Files Created
1. `/workspaces/Trad/ops/scripts/tail_api_logs.sh`:
   - Convenient log tailing script for debugging

## Troubleshooting

### If Jobs Still Get Stuck

1. **Check the logs** using `tail_api_logs.sh`:
   - Look for "Found X training worker PIDs"
   - Check if any PIDs show >50% CPU
   - See if kill commands succeeded

2. **Manual cleanup** (temporary fix):
   ```bash
   ssh root@138.68.245.159
   ps aux | grep "training/worker.py" | grep -v grep
   kill -9 <PID_OF_HIGH_CPU_PROCESS>
   systemctl restart trad-worker.service
   cd /srv/trad && . .venv/bin/activate && python training/cleanup_orphaned_jobs.py
   ```

3. **Check for exceptions** in the cancel function:
   - Look for "Failed to kill worker processes" in logs
   - Check if subprocess commands have permissions
   - Verify systemctl can restart service

### Common Issues

**Issue**: Process not killed even though detected  
**Solution**: Check CPU parsing - might need to adjust split() logic

**Issue**: Multiple processes but none show high CPU  
**Solution**: Job might be in I/O wait - consider lowering threshold or checking process age

**Issue**: Worker doesn't restart  
**Solution**: Check systemd permissions - API needs sudo access for systemctl

## Next Steps

1. **Test the fix** with cancel → start new job flow
2. **Monitor production** for any zombie processes
3. **Consider enhancements**:
   - Add process age check (kill processes running >30 seconds)
   - Add timeout to training jobs (auto-cancel after X hours)
   - Add health check endpoint showing active PIDs

## Deployment

**Deployed**: October 26, 2025 00:16:30 UTC  
**Server**: 138.68.245.159  
**Services Restarted**: trad-api.service, trad-worker.service  
**Commit**: (pending)

## Related Issues

- Initial zombie process discovery: October 25, 2025
- First fix attempt: Added pgrep + kill logic
- Enhanced fix: Added comprehensive logging + worker restart
- This version: v2 with detailed diagnostics
