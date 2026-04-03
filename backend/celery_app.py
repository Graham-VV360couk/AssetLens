"""Celery application — Redis broker, no beat scheduler."""
import os
from celery import Celery

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

celery_app = Celery(
    'assetlens',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['backend.tasks.enrichment'],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
