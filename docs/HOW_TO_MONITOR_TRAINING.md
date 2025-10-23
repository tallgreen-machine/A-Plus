# How to Monitor Training Jobs

## 🎯 Three Ways to Check Training Progress

### **Method 1: Real-Time Progress Monitoring (Recommended)**

Use the provided monitoring script:

```bash
# Start a training job
JOB_RESPONSE=$(curl -s -X POST http://138.68.245.159:8000/api/v2/training/start \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "LIQUIDITY_SWEEP",
    "symbol": "BTC/USDT",
    "exchange": "binanceus",
    "timeframe": "5m",
    "optimizer": "bayesian",
    "lookback_days": 30,
    "n_iterations": 20,
    "run_validation": false
  }')

# Extract job ID
JOB_ID=$(echo "$JOB_RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d\" -f4)
echo "Job ID: $JOB_ID"

# Monitor progress
./monitor_training.sh "$JOB_ID"
```

**Output:**
```
🎯 Monitoring Training Job: 38c57fee-1a34-4d12-9c49-2e95d59c6d0d
===============================================

[01]  25.0% | Data Collection      | Iter:  N/A | Best: N/A
[02]  25.0% | Data Collection      | Iter:  N/A | Best: N/A
[03]  25.0% | Optimization         | Iter:    1 | Best: 0.523
[04]  28.5% | Optimization         | Iter:    3 | Best: 1.245
[05]  35.2% | Optimization         | Iter:    8 | Best: 1.856
...
[20]  95.0% | Saving Configuration | Iter:   20 | Best: 2.145
✅ Training Complete!
```

---

### **Method 2: API Progress Endpoint**

Poll the progress endpoint directly:

```bash
# Get real-time progress
curl -s "http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}/progress" | python3 -m json.tool
```

**Response Example:**
```json
{
  "job_id": "38c57fee-1a34-4d12-9c49-2e95d59c6d0d",
  "percentage": 45.5,
  "current_step": "Optimization",
  "step_number": 2,
  "total_steps": 4,
  "step_percentage": 45.0,
  "step_details": {
    "optimizer": "bayesian",
    "n_calls": 20
  },
  "started_at": "2025-10-23T06:33:20",
  "updated_at": "2025-10-23T06:35:42",
  "estimated_completion": "2025-10-23T06:38:15",
  "current_iteration": 9,
  "total_iterations": 20,
  "best_score": 1.856,
  "current_score": 1.423,
  "best_params": {
    "pierce_depth": 0.15,
    "volume_spike_threshold": 2.5,
    "reversal_candles": 3
  },
  "is_complete": false,
  "error_message": null
}
```

**Key Fields:**
- **percentage**: Overall progress (0-100%)
- **current_step**: Current workflow step
- **current_iteration**: Optimizer iteration number
- **best_score**: Best Sharpe ratio found so far
- **estimated_completion**: ETA timestamp
- **is_complete**: Whether training finished

---

### **Method 3: Database Queries**

Check job status directly in the database:

```bash
# List all training jobs
ssh root@138.68.245.159 'export PGPASSWORD="TRAD123!" && psql -h localhost -U traduser -d trad -c "
SELECT 
  job_id, 
  status, 
  strategy, 
  symbol, 
  optimizer,
  progress_pct,
  best_score,
  created_at,
  duration_seconds
FROM training_jobs 
ORDER BY created_at DESC 
LIMIT 10;
"'
```

```bash
# Check specific job details
ssh root@138.68.245.159 'export PGPASSWORD="TRAD123!" && psql -h localhost -U traduser -d trad -c "
SELECT * FROM training_jobs WHERE job_id = '\''YOUR_JOB_ID'\'';
"'
```

```bash
# Check progress tracking
ssh root@138.68.245.159 'export PGPASSWORD="TRAD123!" && psql -h localhost -U traduser -d trad -c "
SELECT 
  job_id,
  percentage,
  current_step,
  current_iteration,
  total_iterations,
  best_score,
  is_complete,
  updated_at
FROM training_progress 
WHERE job_id = '\''YOUR_JOB_ID'\'';
"'
```

---

## 📊 Training Workflow Steps

Training progresses through 4 steps:

| Step | Name | Progress | Description |
|------|------|----------|-------------|
| 1 | Data Collection | 0-25% | Fetch OHLCV from database, calculate indicators |
| 2 | Optimization | 25-75% | Run optimizer (Grid/Random/Bayesian), test parameters |
| 3 | Validation | 75-95% | Walk-forward validation (optional) |
| 4 | Save Configuration | 95-100% | Write best config to `trained_configurations` table |

**Note:** Step 2 (Optimization) provides the most detailed metrics:
- `current_iteration` / `total_iterations`
- `best_score` (Sharpe ratio)
- `current_score` (current iteration's score)
- `best_params` (best parameters found so far)

---

## 🔍 Common Monitoring Tasks

### Check if training is running
```bash
curl -s "http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}" | grep -o '"status":"[^"]*"'
```

### Get current step
```bash
curl -s "http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}/progress" | grep -o '"current_step":"[^"]*"'
```

### Get best score
```bash
curl -s "http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}/progress" | grep -o '"best_score":[0-9.]*'
```

### Check if complete
```bash
COMPLETE=$(curl -s "http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}/progress" | grep -o '"is_complete":[a-z]*' | cut -d: -f2)
if [ "$COMPLETE" == "true" ]; then
  echo "Training complete!"
else
  echo "Still running..."
fi
```

### Get ETA
```bash
curl -s "http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}/progress" | grep -o '"estimated_completion":"[^"]*"'
```

---

## 🎨 Frontend Integration (Strategy Studio UI)

### Polling Pattern
```javascript
async function monitorTraining(jobId) {
  const interval = setInterval(async () => {
    const response = await fetch(
      `http://138.68.245.159:8000/api/v2/training/jobs/${jobId}/progress`
    );
    const progress = await response.json();
    
    // Update UI
    updateProgressBar(progress.percentage);
    updateStepIndicator(progress.current_step);
    
    if (progress.current_iteration) {
      updateOptimizerStats({
        iteration: `${progress.current_iteration}/${progress.total_iterations}`,
        bestScore: progress.best_score?.toFixed(4),
        currentScore: progress.current_score?.toFixed(4),
        bestParams: progress.best_params
      });
    }
    
    if (progress.estimated_completion) {
      updateETA(progress.estimated_completion);
    }
    
    // Check completion
    if (progress.is_complete) {
      clearInterval(interval);
      handleCompletion(progress);
    }
  }, 2000); // Poll every 2 seconds
}
```

### UI Components to Display

**Progress Bar:**
```
Training BTC/USDT on binanceus (5m)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45%
ETA: ~3 minutes remaining
```

**Step Indicator:**
```
✓ Data Collection → [Optimizing...] → Validation → Save Config
```

**Optimizer Dashboard (Step 2 only):**
```
Bayesian Optimizer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Iteration: 9 / 20
Best Score: 1.8560
Current Score: 1.4230

Best Parameters:
• pierce_depth: 0.15
• volume_spike_threshold: 2.5
• reversal_candles: 3
• atr_multiplier_sl: 2.0
```

---

## 🐛 Troubleshooting

### Job not starting
```bash
# Check job status
curl -s "http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}" | grep status

# Check dashboard service
ssh root@138.68.245.159 'systemctl status dashboard.service'

# Check logs
ssh root@138.68.245.159 'tail -50 /var/log/trad-dashboard.log'
```

### No progress updates
```bash
# Verify progress table exists
ssh root@138.68.245.159 'export PGPASSWORD="TRAD123!" && psql -h localhost -U traduser -d trad -c "\d training_progress"'

# Check for progress records
ssh root@138.68.245.159 'export PGPASSWORD="TRAD123!" && psql -h localhost -U traduser -d trad -c "SELECT COUNT(*) FROM training_progress;"'
```

### Training failed
```bash
# Get error message
curl -s "http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}" | grep -o '"error_message":"[^"]*"'

# Get full error trace
ssh root@138.68.245.159 'export PGPASSWORD="TRAD123!" && psql -h localhost -U traduser -d trad -c "SELECT error_trace FROM training_jobs WHERE job_id = '\''YOUR_JOB_ID'\'';"'
```

---

## 📝 Quick Reference

### Start Training
```bash
curl -X POST http://138.68.245.159:8000/api/v2/training/start \
  -H "Content-Type: application/json" \
  -d '{"strategy":"LIQUIDITY_SWEEP","symbol":"BTC/USDT","exchange":"binanceus","timeframe":"5m","optimizer":"bayesian","lookback_days":30,"n_iterations":20,"run_validation":false}'
```

### Get Progress
```bash
curl http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}/progress
```

### Get Job Info
```bash
curl http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}
```

### List All Jobs
```bash
curl http://138.68.245.159:8000/api/v2/training/jobs
```

### Get Results
```bash
curl http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}/results
```

### Cancel Job
```bash
curl -X DELETE http://138.68.245.159:8000/api/v2/training/jobs/{JOB_ID}
```

---

## ✅ Testing Checklist

- [ ] Training job starts successfully
- [ ] Progress updates appear in real-time
- [ ] Step transitions are tracked
- [ ] Optimizer metrics (iteration, scores) update
- [ ] ETA calculation works
- [ ] Training completes successfully
- [ ] Results saved to `trained_configurations` table
- [ ] Error handling works (if job fails)
- [ ] Progress monitoring script works
- [ ] All API endpoints respond correctly

---

## 🎯 Current Live Training

**Job ID:** `38c57fee-1a34-4d12-9c49-2e95d59c6d0d`

Monitor it:
```bash
./monitor_training.sh 38c57fee-1a34-4d12-9c49-2e95d59c6d0d
```

Or via API:
```bash
curl -s "http://138.68.245.159:8000/api/v2/training/jobs/38c57fee-1a34-4d12-9c49-2e95d59c6d0d/progress" | python3 -m json.tool
```

---

**Happy Training!** 🚀
