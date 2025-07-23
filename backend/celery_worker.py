#!/usr/bin/env python3
"""
Celery worker entry point for CheckGuard AI.

This script starts a Celery worker that processes background analysis tasks.
"""

import os
import sys
import logging
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.tasks.celery_app import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/celery_worker.log') if os.path.exists('/app/logs') else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Start the Celery worker."""
    logger.info("Starting CheckGuard Celery worker...")
    
    # Worker configuration
    worker_args = [
        'worker',
        '--loglevel=info',
        '--concurrency=2',  # Limit concurrency for resource management
        '--queues=analysis',  # Only process analysis tasks
        '--prefetch-multiplier=1',  # Important for long-running tasks
        '--max-tasks-per-child=10',  # Restart worker after 10 tasks to prevent memory leaks
        '--time-limit=7200',  # 2 hour hard time limit
        '--soft-time-limit=6000',  # 100 minute soft time limit
    ]
    
    # Add optimization flags
    worker_args.extend([
        '--optimization=fair',
        '--without-gossip',
        '--without-mingle',
        '--without-heartbeat',
    ])
    
    logger.info(f"Starting worker with args: {' '.join(worker_args)}")
    
    # Start the worker
    celery_app.worker_main(worker_args)

if __name__ == '__main__':
    main()