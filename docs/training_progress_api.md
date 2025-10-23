# Training Progress Tracking API

## Overview

Real-time progress tracking for V2 training jobs. This enables the Strategy Studio UI to display live progress updates, ETAs, and optimizer metrics during training.

## Database Schema

### `training_progress` Table

Stores real-time progress snapshots for each training job.

```sql
CREATE TABLE training_progress (
    id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Overall progress
    percentage FLOAT NOT NULL DEFAULT 0.0,     -- 0.0 to 100.0
    current_step VARCHAR(100) NOT NULL,        -- Step name
    step_number INTEGER NOT NULL DEFAULT 1,    -- 1-4
    total_steps INTEGER NOT NULL DEFAULT 4,
    
    -- Step-specific progress
    step_percentage FLOAT NOT NULL DEFAULT 0.0,
    step_details JSONB,                        -- Step metadata
    
    -- Time tracking
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estimated_completion TIMESTAMPTZ,
    
    -- Optimizer metrics (real-time monitoring)
    current_iteration INTEGER,
    total_iterations INTEGER,
    best_score FLOAT,
    current_score FLOAT,
    best_params JSONB,
    
    -- Status
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT
);
```

## Training Workflow Steps

The training system has **4 major steps**, each with different weights:

| Step | Name | Weight | Description |
|------|------|--------|-------------|
| 1 | Data Collection | 25% | Fetch OHLCV data from database |
| 2 | Optimization | 50% | Run optimizer (Grid/Random/Bayesian) |
| 3 | Validation | 20% | Walk-forward validation (optional) |
| 4 | Save Configuration | 5% | Write to `trained_configurations` |

**Overall Progress Calculation:**
```
overall_pct = (completed_steps_weight * 100) + (current_step_weight * step_pct)
```

Example: If in Optimization (step 2) at 60% progress:
- Completed: Data Collection (25%)
- Current: Optimization (50% * 0.60 = 30%)
- **Overall: 55%**

## API Endpoint

### GET `/api/v2/training/jobs/{job_id}/progress`

Get real-time progress for a training job.

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier |
| `percentage` | float | Overall progress (0-100) |
| `current_step` | string | Current step name |
| `step_number` | int | Current step (1-4) |
| `total_steps` | int | Total steps (always 4) |
| `step_percentage` | float | Progress within current step (0-100) |
| `step_details` | object | Step-specific metadata |
| `started_at` | datetime | When training started |
| `updated_at` | datetime | Last progress update |
| `estimated_completion` | datetime | ETA (null if not enough data) |
| `current_iteration` | int | Current optimizer iteration (during optimization) |
| `total_iterations` | int | Total optimizer iterations |
| `best_score` | float | Best score found so far |
| `current_score` | float | Score of current iteration |
| `best_params` | object | Best parameters found so far |
| `is_complete` | boolean | Whether training finished |
| `error_message` | string | Error message (if failed) |

**Example Response:**

```json
{
  "job_id": "abc123-def456",
  "percentage": 62.5,
  "current_step": "Optimization",
  "step_number": 2,
  "total_steps": 4,
  "step_percentage": 75.0,
  "step_details": {
    "optimizer": "bayesian",
    "n_calls": 50
  },
  "started_at": "2025-10-23T06:00:00Z",
  "updated_at": "2025-10-23T06:10:25Z",
  "estimated_completion": "2025-10-23T06:15:30Z",
  "current_iteration": 38,
  "total_iterations": 50,
  "best_score": 1.85,
  "current_score": 1.42,
  "best_params": {
    "pierce_depth": 0.15,
    "volume_spike_threshold": 2.5,
    "reversal_candles": 3
  },
  "is_complete": false,
  "error_message": null
}
```

**Status Codes:**

- `200 OK` - Success
- `404 Not Found` - Job doesn't exist
- `500 Internal Server Error` - Server error

## Frontend Integration

### Polling Pattern

The Strategy Studio UI should poll this endpoint every 2-3 seconds during training:

```javascript
async function pollTrainingProgress(jobId) {
  const interval = 2000; // 2 seconds
  
  while (true) {
    const response = await fetch(
      `/api/v2/training/jobs/${jobId}/progress`
    );
    
    if (!response.ok) {
      console.error('Failed to fetch progress');
      await sleep(interval);
      continue;
    }
    
    const progress = await response.json();
    
    // Update UI
    updateProgressBar(progress.percentage);
    updateStepIndicator(progress.step_number, progress.current_step);
    updateOptimizer Stats(progress);
    
    // Check completion
    if (progress.is_complete) {
      if (progress.error_message) {
        showError(progress.error_message);
      } else {
        showSuccess(progress.best_score, progress.best_params);
      }
      break;
    }
    
    await sleep(interval);
  }
}
```

### UI Components to Update

1. **Overall Progress Bar**
   - Display `percentage` (0-100)
   - Show `estimated_completion` as ETA

2. **Step Indicator**
   - Highlight `current_step` (1-4)
   - Show step name: Data Collection → Optimization → Validation → Save

3. **Optimizer Stats Panel** (during Optimization step)
   - Iteration counter: `current_iteration` / `total_iterations`
   - Best score: `best_score`
   - Current score: `current_score`
   - Best parameters: `best_params` (formatted)

4. **Status Messages**
   - Show `current_step` with `step_percentage`
   - Display `error_message` if failed

## Example: Complete Training Lifecycle

### Step 1: Data Collection (0-25%)
```json
{
  "percentage": 12.5,
  "current_step": "Data Collection",
  "step_number": 1,
  "step_percentage": 50.0,
  "step_details": {
    "symbol": "BTC/USDT",
    "exchange": "binanceus",
    "timeframe": "5m",
    "lookback_days": 90
  }
}
```

### Step 2: Optimization (25-75%)
```json
{
  "percentage": 55.0,
  "current_step": "Optimization",
  "step_number": 2,
  "step_percentage": 60.0,
  "current_iteration": 30,
  "total_iterations": 50,
  "best_score": 1.85,
  "current_score": 1.42,
  "best_params": {
    "pierce_depth": 0.15,
    "volume_spike_threshold": 2.5
  },
  "estimated_completion": "2025-10-23T06:15:30Z"
}
```

### Step 3: Validation (75-95%)
```json
{
  "percentage": 85.0,
  "current_step": "Validation",
  "step_number": 3,
  "step_percentage": 50.0,
  "step_details": {
    "train_window_days": 60,
    "test_window_days": 30,
    "gap_days": 7
  }
}
```

### Step 4: Complete (100%)
```json
{
  "percentage": 100.0,
  "current_step": "Complete",
  "step_number": 4,
  "step_percentage": 100.0,
  "is_complete": true,
  "best_score": 1.85,
  "best_params": {
    "pierce_depth": 0.15,
    "volume_spike_threshold": 2.5,
    "reversal_candles": 3
  }
}
```

## Testing

Run the progress tracking test script:

```bash
# Start new training and monitor
python test_progress_tracking.py

# Monitor existing job
python test_progress_tracking.py <job_id>
```

The script will:
1. Start a training job (if no job_id provided)
2. Poll the progress endpoint every 2 seconds
3. Display real-time updates
4. Show completion status

**Example Output:**
```
[06:10:25] Step 2/4: Optimization
  Overall: 55.0%  |  Step: 60.0%
  Iteration: 30/50
  Best Score: 1.8500
  Current Score: 1.4200
  ETA: 2025-10-23T06:15:30Z
  [█████████████████████████████░░░░░░░░░░░░░░░░░░░░░] 55.0%
```

## Architecture Notes

### ProgressTracker Class (`training/progress_tracker.py`)

The `ProgressTracker` is used by the training workflow to publish updates:

```python
# In training workflow
progress = ProgressTracker(job_id=job_id, db_url=db_url)

# Start step
await progress.start('data_collection', {'symbol': 'BTC/USDT'})

# Update within step
await progress.update(
    step_percentage=50.0,
    iteration=30,
    total_iterations=50,
    best_score=1.85
)

# Complete
await progress.complete()

# Or mark as failed
await progress.error("Optimization failed: ...")
```

### Database Updates

Progress updates use **UPSERT** (INSERT ... ON CONFLICT UPDATE):
- Each job_id has **one** progress record
- Updates are atomic and non-blocking
- Frontend polls read-only queries

### Performance

- Progress updates: ~5-10ms (async, non-blocking)
- Frontend polls: ~2-3 second intervals
- Database load: Minimal (single row per job)
- No WebSocket needed (simple REST polling is sufficient)

## Future Enhancements

1. **WebSocket Support** - Real-time push instead of polling
2. **Progress History** - Store historical snapshots for replay
3. **Cancellation Support** - Allow user to stop training mid-flight
4. **Multi-Job Dashboard** - Monitor multiple training jobs simultaneously
5. **Progress Notifications** - Email/Slack when training completes
