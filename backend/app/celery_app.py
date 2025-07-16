from celery import Celery
from app.config import Config

# 创建Celery实例
celery_app = Celery(
    'video_monitor',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['app.tasks.video_processing']
)

# Celery配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_routes={
        'app.tasks.video_processing.*': {'queue': 'video_processing'},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)