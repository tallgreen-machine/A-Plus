#!/bin/bash
# Quick training progress monitor

JOB_ID="$1"

if [ -z "$JOB_ID" ]; then
  echo "Usage: $0 <job_id>"
  exit 1
fi

echo "🎯 Monitoring Training Job: $JOB_ID"
echo "==============================================="
echo ""

for i in {1..60}; do
  PROGRESS=$(curl -s "http://138.68.245.159:8000/api/v2/training/jobs/$JOB_ID/progress")
  
  PCT=$(echo "$PROGRESS" | grep -o '"percentage":[0-9.]*' | cut -d: -f2)
  STEP=$(echo "$PROGRESS" | grep -o '"current_step":"[^"]*"' | cut -d\" -f4)
  ITER=$(echo "$PROGRESS" | grep -o '"current_iteration":[0-9]*' | cut -d: -f2)
  BEST=$(echo "$PROGRESS" | grep -o '"best_score":[0-9.]*' | cut -d: -f2)
  COMPLETE=$(echo "$PROGRESS" | grep -o '"is_complete":[a-z]*' | cut -d: -f2)
  
  [ -z "$PCT" ] && PCT="0"
  [ -z "$STEP" ] && STEP="Pending"
  [ -z "$ITER" ] && ITER="N/A"
  [ -z "$BEST" ] && BEST="N/A"
  
  printf "[%02d] %5.1f%% | %-20s | Iter: %4s | Best: %s\n" "$i" "$PCT" "$STEP" "$ITER" "$BEST"
  
  if [ "$COMPLETE" == "true" ]; then
    echo ""
    echo "✅ Training Complete!"
    echo ""
    echo "Final Progress:"
    echo "$PROGRESS" | python3 -m json.tool 2>/dev/null || echo "$PROGRESS"
    break
  fi
  
  sleep 3
done
