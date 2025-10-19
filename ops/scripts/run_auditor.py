# ops/scripts/run_auditor.py
import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from policy.reliability_engine import PatternAuditor

if __name__ == "__main__":
    auditor = PatternAuditor()
    auditor.run_weekly_audit()
