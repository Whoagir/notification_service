import random
import time
from celery import shared_task
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.future import select
from app.models.notification import Notification
from app.config.database import DATABASE_URL


sync_engine = create_engine(
    DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True
)
sync_session = sessionmaker(sync_engine)

# Синхронная версия функции анализа текста
def analyze_text(text: str) -> dict:
    """Имитация работы AI API с задержкой 1-3 секунды."""
    time.sleep(random.uniform(1, 3))  # Используем time.sleep вместо asyncio.sleep
    if any(word in text.lower() for word in ["error", "exception", "failed"]):
        category = "critical"
        confidence = random.uniform(0.7, 0.95)
    elif any(word in text.lower() for word in ["warning", "attention", "careful"]):
        category = "warning"
        confidence = random.uniform(0.6, 0.9)
    else:
        category = "info"
        confidence = random.uniform(0.8, 0.99)
    return {
        "category": category,
        "confidence": confidence,
        "keywords": random.sample(text.split(), min(3, len(text.split())))
    }

@shared_task
def process_notification(notification_id: str):
    """Синхронная задача Celery для обработки уведомления."""
    with sync_session() as db:  # Создаём синхронную сессию базы данных
        # Находим уведомление по ID
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if notification:
            # Обновляем статус на "processing"
            notification.processing_status = "processing"
            db.commit()

            # Анализируем текст
            analysis = analyze_text(notification.text)

            # Обновляем уведомление с результатами анализа
            notification.category = analysis["category"]
            notification.confidence = analysis["confidence"]
            notification.processing_status = "completed"
            db.commit()