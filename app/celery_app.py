from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "pos_system",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Bogota",
    enable_utc=False,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_scheduler="celery.beat.PersistentScheduler",
    beat_schedule={
        "check-shift-end-alerts": {
            "task": "app.tasks.shift_tasks.check_shift_end_alerts",
            "schedule": 300.0,
        },
        "check-weekly-hour-limits": {
            "task": "app.tasks.shift_tasks.check_weekly_hour_limits",
            "schedule": 3600.0,
        },
        "daily-sales-report": {
            "task": "app.tasks.report_tasks.daily_sales_report",
            "schedule": crontab(hour=23, minute=55),
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])