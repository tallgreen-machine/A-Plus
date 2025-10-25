"""
Cleanup Orphaned Training Jobs

Detects and fixes training jobs that are stuck in 'running' status
but have no active RQ worker processing them.

Run periodically or manually to clean up after crashes/restarts.
"""

import asyncio
import asyncpg
from redis import Redis
from rq import Queue
from rq.job import Job
import os
from datetime import datetime, timedelta


def get_db_url() -> str:
    """Get database URL from environment."""
    db_host = os.getenv('DB_HOST', 'localhost')
    db_user = os.getenv('DB_USER', 'traduser')
    db_password = os.getenv('DB_PASSWORD', 'TRAD123!')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'trad')
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


async def cleanup_orphaned_jobs():
    """
    Find and fix orphaned training jobs.
    
    A job is orphaned if:
    - Status is 'running' in database
    - BUT no RQ job is actually executing it
    - OR RQ job status is failed/cancelled but DB still shows running
    """
    db_url = get_db_url()
    conn = await asyncpg.connect(db_url)
    
    # Get all 'running' jobs
    running_jobs = await conn.fetch(
        "SELECT id, rq_job_id, started_at FROM training_jobs WHERE status = 'running'"
    )
    
    if not running_jobs:
        print("✅ No running jobs to check")
        await conn.close()
        return
    
    print(f"🔍 Checking {len(running_jobs)} running job(s)...")
    
    # Connect to Redis
    redis_conn = Redis(host='localhost', port=6379, db=0)
    
    orphaned_count = 0
    
    for job in running_jobs:
        job_id = job['id']
        rq_job_id = job['rq_job_id']
        started_at = job['started_at']
        
        if not rq_job_id:
            # No RQ job ID - definitely orphaned
            print(f"  ❌ Job {job_id}: No RQ job ID")
            await conn.execute(
                """
                UPDATE training_jobs 
                SET status = 'failed', 
                    error_message = 'Orphaned: No RQ job ID found',
                    completed_at = NOW()
                WHERE id = $1
                """,
                job_id
            )
            orphaned_count += 1
            continue
        
        # Check RQ job status
        try:
            rq_job = Job.fetch(rq_job_id, connection=redis_conn)
            rq_status = rq_job.get_status()
            
            # If RQ job is not actually running, mark as orphaned
            if rq_status in ('finished', 'failed', 'canceled', 'stopped'):
                print(f"  ❌ Job {job_id}: RQ status is '{rq_status}' but DB shows 'running'")
                
                # Update to match RQ status
                if rq_status == 'finished':
                    new_status = 'completed'
                elif rq_status == 'canceled':
                    new_status = 'cancelled'
                else:
                    new_status = 'failed'
                
                await conn.execute(
                    """
                    UPDATE training_jobs 
                    SET status = $2, 
                        error_message = $3,
                        completed_at = NOW()
                    WHERE id = $1
                    """,
                    job_id,
                    new_status,
                    f"Orphaned: RQ job status was '{rq_status}'"
                )
                orphaned_count += 1
            
            elif rq_status == 'started':
                # Job is legitimately running
                elapsed = datetime.utcnow() - started_at.replace(tzinfo=None)
                print(f"  ✅ Job {job_id}: Running (elapsed: {elapsed})")
            
            else:
                # Queued or deferred
                print(f"  ⏳ Job {job_id}: RQ status is '{rq_status}'")
        
        except Exception as e:
            # RQ job not found - orphaned
            print(f"  ❌ Job {job_id}: RQ job not found - {e}")
            await conn.execute(
                """
                UPDATE training_jobs 
                SET status = 'failed', 
                    error_message = 'Orphaned: RQ job not found after worker restart',
                    completed_at = NOW()
                WHERE id = $1
                """,
                job_id
            )
            orphaned_count += 1
    
    await conn.close()
    
    if orphaned_count > 0:
        print(f"\n🧹 Cleaned up {orphaned_count} orphaned job(s)")
    else:
        print("\n✅ No orphaned jobs found")


if __name__ == "__main__":
    asyncio.run(cleanup_orphaned_jobs())
