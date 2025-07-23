from celery import Celery
from ..core.config import settings

# Create Celery app instance
celery_app = Celery(
    "checkguard_tasks",
    include=['app.tasks.analysis_tasks']
)

# Configure Celery
celery_app.conf.update(
    # Broker and Backend Configuration
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    
    # Task Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone Configuration
    timezone='UTC',
    enable_utc=True,
    
    # Task Timeout Configuration (Enhanced for streaming tasks)
    task_soft_time_limit=600,  # 10 minutes soft limit (allows cleanup)
    task_time_limit=900,  # 15 minutes hard limit (kills task)
    broker_transport_options={
        'visibility_timeout': 3600,  # 1 hour visibility (for long tasks)
        'priority_steps': list(range(10)),  # Enable task priorities
    },
    
    # Task Routing
    task_routes={
        'app.tasks.analysis_tasks.analyze_check_async': {'queue': 'analysis'},
        'app.tasks.analysis_tasks.analyze_check_streaming': {'queue': 'analysis'},
    },
    
    # Worker Configuration - Enhanced resource limits for streaming
    worker_prefetch_multiplier=1,  # Prevent resource hoarding (critical for memory management)
    task_acks_late=True,  # Reliability for long tasks (prevent message loss on worker crashes)
    worker_disable_rate_limits=True,
    worker_max_memory_per_child=512 * 1024,  # 512MB memory limit per worker child (prevents OOM)
    worker_max_tasks_per_child=50,  # Restart workers after 50 tasks to prevent memory leaks
    worker_concurrency=2,  # Limit concurrent tasks for resource management
    
    # Result Backend Configuration
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Task Execution
    task_ignore_result=False,
    task_store_eager_result=True,
    
    # Error Handling - Enhanced for resource protection
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies (prevents message loss)
    task_default_retry_delay=60,  # Wait 60s before retry
    task_max_retries=3,  # Maximum 3 retry attempts
    
    # Resource protection settings
    worker_hijack_root_logger=False,  # Preserve application logging
    worker_log_color=False,  # Disable color logging for production
    worker_send_task_events=True,  # Enable task monitoring events
    task_send_sent_event=True,  # Track task dispatch events
    
    # Memory and performance optimizations
    task_compression='gzip',  # Compress task payloads
    result_compression='gzip',  # Compress results
    task_always_eager=False,  # Never run tasks synchronously (important!)
    
    # Connection pool settings for reliability
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
)

# Task autodiscovery
celery_app.autodiscover_tasks(['app.tasks'])