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
    
    # Task Timeout Configuration (Critical for long-running tasks)
    broker_transport_options={'visibility_timeout': settings.BROKER_VISIBILITY_TIMEOUT},
    task_soft_time_limit=settings.TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.TASK_TIME_LIMIT,
    
    # Task Routing
    task_routes={
        'app.tasks.analysis_tasks.analyze_check_async': {'queue': 'analysis'},
    },
    
    # Worker Configuration
    worker_prefetch_multiplier=1,  # Important for long tasks
    task_acks_late=True,
    worker_disable_rate_limits=True,
    
    # Result Backend Configuration
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Task Execution
    task_ignore_result=False,
    task_store_eager_result=True,
    
    # Error Handling
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Task autodiscovery
celery_app.autodiscover_tasks(['app.tasks'])