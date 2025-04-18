from celery import Celery
from dotenv import load_dotenv
from app.config.logging_config import setup_logging
import os

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем REDIS_URL из переменных окружения
redis_url = os.getenv("REDIS_URL")

if not redis_url:
    raise ValueError("REDIS_URL не установлен в переменных окружения")

# Создаём экземпляр Celery
celery_app = Celery(
    "notification_service",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

setup_logging()