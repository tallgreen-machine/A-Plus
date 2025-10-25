# Automatic Job Cleanup on Cancellation

## Overview

The training queue now automatically cleans up orphaned jobs when you cancel a training job from the UI.

## How It Works

### Before (Manual Cleanup Required)

1. User clicks "Cancel" on running job
2. RQ job gets cancelled
3. Database still shows "running"
4. Worker might be stuck with orphaned process
5. **Manual fix required**: Run `python training/cleanup_orphaned_jobs.py`

### After (Automatic Cleanup)

1. User clicks "Cancel" on running job
2. System automatically:
   - Cancels RQ job
   - Kills worker process gracefully
   - Updates database to "cancelled"
   - Scans for any other orphaned jobs
   - Cleans up orphaned state
3. **Worker ready immediately** for next job

## What Gets Cleaned Up

The automatic cleanup process:

1. **Cancels the target job**:
   - Sends cancel signal to RQ
   - Kills the worker process
   - Updates database status

2. **Scans for orphaned jobs**:
   - Checks all "running" jobs in database
   - Verifies RQ worker status matches
   - Syncs any mismatches

3. **Fixes orphaned state**:
   - Jobs with no RQ ID → marked as failed
   - Jobs where RQ finished but DB shows running → synced
   - Jobs where RQ job not found → marked as failed

## Benefits

✅ **No manual intervention needed** - Just click Cancel in UI  
✅ **Worker always ready** - Next job can start immediately  
✅ **Consistent state** - Database always matches reality  
✅ **Better UX** - Users don't get confused by stuck jobs  

## Technical Details

### API Endpoint: `DELETE /api/training/{job_id}`

**Enhanced behavior**:
```python
1. Fetch job from database
2. Cancel RQ job (if exists)
3. Kill worker process (graceful)
4. Update database status to 'cancelled'
5. Run cleanup_orphaned_training_jobs()
6. Return success response
```

### Cleanup Function: `cleanup_orphaned_training_jobs()`

**What it checks**:
- All jobs with status='running' in database
- Fetches corresponding RQ job status
- Syncs mismatches between DB and RQ

**Status mappings**:
- RQ `finished` → DB `completed`
- RQ `failed` → DB `failed`
- RQ `canceled` → DB `failed` (with note)
- RQ `not found` → DB `failed` (orphaned)

## Usage

### From UI (Automatic)

1. Go to Strategy Studio
2. Click "Cancel" on any running/queued job
3. ✅ **That's it!** Cleanup happens automatically

### From API (Automatic)

```bash
curl -X DELETE http://localhost:8000/api/training/123
```

Response:
```json
{
  "success": true,
  "message": "Job 123 cancelled successfully",
  "rq_cancelled": true
}
```

### Manual Cleanup (If Needed)

The standalone script still exists for manual checks:

```bash
cd /srv/trad
. .venv/bin/activate
python training/cleanup_orphaned_jobs.py
```

Use this for:
- Checking system health
- Cleaning up after server crashes
- Scheduled maintenance (cron job)

## When Cleanup Runs

**Automatically**:
- ✅ Every time a job is cancelled via UI/API
- ✅ After killing/cancelling any job

**Manually** (if needed):
- After server restart/crash
- Before important training runs
- As part of maintenance routine

## Monitoring

Check cleanup effectiveness:

```sql
-- Count cancelled jobs
SELECT COUNT(*) FROM training_jobs WHERE status = 'cancelled';

-- Find recently cleaned jobs
SELECT id, status, error_message, completed_at 
FROM training_jobs 
WHERE error_message LIKE '%Orphaned%' OR error_message LIKE '%Synced%'
ORDER BY completed_at DESC LIMIT 10;

-- Check for any remaining stuck jobs
SELECT id, status, started_at, 
       EXTRACT(EPOCH FROM (NOW() - started_at)) as stuck_seconds
FROM training_jobs 
WHERE status = 'running' 
  AND started_at < NOW() - INTERVAL '10 minutes';
```

## Files Changed

1. **`/workspaces/Trad/api/training_queue.py`**
   - Enhanced `cancel_training_job()` endpoint
   - Added `cleanup_orphaned_training_jobs()` function
   - Integrated cleanup into cancellation flow

2. **`/workspaces/Trad/training/cleanup_orphaned_jobs.py`**
   - Standalone script (still available)
   - Can be run manually or via cron

## Deployment

✅ Deployed: October 25, 2025 at 23:12 UTC  
✅ Tested: Successfully cleaned job 98  
✅ Status: Active and working  

## Future Enhancements

Possible improvements:
- [ ] Scheduled cleanup (cron every 5 minutes)
- [ ] Cleanup on worker startup
- [ ] Metrics dashboard for cleanup stats
- [ ] Alerts for jobs stuck > 30 minutes
