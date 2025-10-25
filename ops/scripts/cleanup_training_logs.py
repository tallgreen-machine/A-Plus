#!/usr/bin/env python3
"""
Cleanup Training Logs

Removes old training logs to prevent unbounded database growth.
Retention policy: Keep last 7 days OR last 100 jobs worth of logs.
"""

import os
import sys
import asyncpg
import asyncio
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """Get database URL from environment variables."""
    # Try DATABASE_URL first
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Try DB_* environment variables (trad.env format)
    db_host = os.getenv('DB_HOST')
    if db_host:
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME')
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Fallback to localhost
    return "postgresql://traduser:TRAD123!@localhost:5432/trad"


async def cleanup_old_logs(dry_run: bool = False):
    """
    Remove training logs older than 7 days OR beyond last 100 jobs.
    
    Args:
        dry_run: If True, only report what would be deleted without actually deleting
    """
    db_url = get_db_url()
    conn = None
    
    try:
        conn = await asyncpg.connect(db_url)
        
        # Get cutoff date (7 days ago)
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        # Get the 100th most recent job_id
        recent_jobs = await conn.fetch("""
            SELECT DISTINCT job_id
            FROM training_logs
            ORDER BY job_id DESC
            LIMIT 100
        """)
        
        if len(recent_jobs) >= 100:
            job_100th = recent_jobs[99]['job_id']
            
            # Count logs that would be deleted
            count_by_date = await conn.fetchval("""
                SELECT COUNT(*)
                FROM training_logs
                WHERE created_at < $1
            """, cutoff_date)
            
            count_by_job = await conn.fetchval("""
                SELECT COUNT(*)
                FROM training_logs
                WHERE job_id < $1
            """, job_100th)
            
            # Choose the policy that deletes fewer logs (more conservative)
            if count_by_date <= count_by_job:
                policy = 'date'
                count = count_by_date
                logger.info(f"Using date-based policy: Delete logs older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                policy = 'job'
                count = count_by_job
                logger.info(f"Using job-based policy: Delete logs for jobs before #{job_100th}")
            
            if count == 0:
                logger.info("No logs to clean up")
                return
            
            if dry_run:
                logger.info(f"DRY RUN: Would delete {count} log entries ({policy} policy)")
            else:
                # Execute deletion
                if policy == 'date':
                    deleted = await conn.execute("""
                        DELETE FROM training_logs
                        WHERE created_at < $1
                    """, cutoff_date)
                else:
                    deleted = await conn.execute("""
                        DELETE FROM training_logs
                        WHERE job_id < $1
                    """, job_100th)
                
                logger.info(f"Deleted {deleted} log entries ({policy} policy)")
        
        else:
            logger.info(f"Only {len(recent_jobs)} jobs with logs - no cleanup needed yet")
        
        # Get summary stats
        total_logs = await conn.fetchval("SELECT COUNT(*) FROM training_logs")
        total_jobs = await conn.fetchval("SELECT COUNT(DISTINCT job_id) FROM training_logs")
        oldest_log = await conn.fetchval("SELECT MIN(created_at) FROM training_logs")
        
        logger.info(f"Current state: {total_logs} logs across {total_jobs} jobs")
        if oldest_log:
            logger.info(f"Oldest log: {oldest_log.strftime('%Y-%m-%d %H:%M:%S')}")
    
    except Exception as e:
        logger.error(f"Failed to cleanup logs: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        if conn:
            await conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup old training logs')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Show what would be deleted without actually deleting')
    args = parser.parse_args()
    
    asyncio.run(cleanup_old_logs(dry_run=args.dry_run))
