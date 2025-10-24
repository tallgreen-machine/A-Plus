#!/usr/bin/env python3
"""
TradePulse Training Worker

RQ worker process that executes training jobs from the Redis queue.
Runs independently from the FastAPI server for process isolation.

Usage:
    python worker.py

Environment:
    REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    
Systemd:
    Managed by trad-worker.service
    Logs: /var/log/trad-worker.log
"""

import os
import sys
import logging
from redis import Redis
from rq import Worker, Queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/trad-worker.log')
    ]
)

log = logging.getLogger(__name__)


def get_redis_url() -> str:
    """Get Redis URL from environment."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    log.info(f"Using Redis: {redis_url}")
    return redis_url


def main():
    """Run RQ worker."""
    log.info("=" * 60)
    log.info("TradePulse Training Worker Starting")
    log.info("=" * 60)
    
    # Get Redis connection
    redis_url = get_redis_url()
    redis_conn = Redis.from_url(redis_url)
    
    # Test Redis connection
    try:
        redis_conn.ping()
        log.info("✓ Redis connection successful")
    except Exception as e:
        log.error(f"✗ Redis connection failed: {e}")
        sys.exit(1)
    
    # Create worker and listen on 'training' queue (no Connection context in RQ 2.x)
    worker = Worker(
        ['training'],  # Queue names to listen to
        connection=redis_conn,
        name='training-worker',
        log_job_description=True
    )
    
    log.info("Worker configured:")
    log.info(f"  - Queues: {worker.queue_names()}")
    log.info(f"  - Name: {worker.name}")
    log.info("Waiting for jobs...")
    
    # Start processing jobs (blocks until terminated)
    worker.work(with_scheduler=False)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nWorker stopped by user")
        sys.exit(0)
    except Exception as e:
        log.error(f"Worker crashed: {e}", exc_info=True)
        sys.exit(1)
