"""
Celery configuration for background tasks.
"""

from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "discovery_service",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.scan_tasks", "app.workers.health_tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "health-check-every-5-minutes": {
        "task": "app.workers.health_tasks.run_health_checks",
        "schedule": 300.0,  # 5 minutes
    },
    "cleanup-old-scans-daily": {
        "task": "app.workers.scan_tasks.cleanup_old_scans",
        "schedule": 86400.0,  # 24 hours
    },
}
