"""
Celery Application Factory for Workflow Service

Provides async workflow execution through Celery workers.
"""

from celery import Celery

from config import get_settings


# Get settings
settings = get_settings()

# Create Celery app with Redis broker and result backend
celery_app = Celery(
    "workflow-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer=settings.celery_task_serializer,
    result_serializer=settings.celery_result_serializer,
    accept_content=settings.celery_accept_content,
    # Timezone
    timezone=settings.celery_timezone,
    enable_utc=True,
    # Task execution settings
    task_track_started=settings.celery_task_track_started,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_soft_time_limit,
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    task_ignore_result=False,
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    # Redis key prefix for isolation
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
)

# Task routing
celery_app.conf.task_routes = {
    "tasks.execute_workflow_task": {"queue": "workflows"},
    "tasks.execute_step_task": {"queue": "workflows"},
    "tasks.cleanup_stale_executions": {"queue": "maintenance"},
}


def get_celery_app() -> Celery:
    """Get the Celery application instance."""
    return celery_app
