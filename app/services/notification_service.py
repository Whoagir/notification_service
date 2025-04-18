from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationCreate
from app.models.notification import Notification
from uuid import UUID, uuid4
from datetime import datetime
from app.exceptions import NotificationNotFoundException
from app.celery_app import celery_app
from sqlalchemy import update


class NotificationService:
    def __init__(self, repo: NotificationRepository):
        self.repo = repo

    async def get_notification(self, notification_id: UUID) -> Notification:
        """Получить уведомление по ID"""
        notification = await self.repo.get_by_id(notification_id)
        if not notification:
            raise NotificationNotFoundException(str(notification_id))
        return notification

    async def get_notifications(self, user_id: UUID, skip: int, limit: int) -> list[Notification]:
        """Получить список уведомлений пользователя"""
        return await self.repo.get_list(user_id, skip, limit)

    async def create_notification(self, notification_data: NotificationCreate) -> Notification:
        """Создать новое уведомление и запустить обработку"""
        new_notification = Notification(
            id=uuid4(),
            user_id=notification_data.user_id,
            title=notification_data.title,
            text=notification_data.text,
            created_at=datetime.utcnow(),
            processing_status="pending"
        )
        created_notification = await self.repo.create(new_notification)

        # Запуск асинхронной обработки
        celery_app.send_task("app.tasks.process_notification", args=[str(created_notification.id)])

        return created_notification

    async def mark_as_read(self, notification_id: UUID) -> Notification:
        """Отметить уведомление как прочитанное"""
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .values(read_at=datetime.utcnow())
            .returning(Notification)
        )
        result = await self.repo.db.execute(stmt)
        notification = result.scalars().first()
        if not notification:
            raise NotificationNotFoundException(str(notification_id))
        return notification

    async def get_status(self, notification_id: UUID) -> dict:
        """Получить статус обработки уведомления"""
        notification = await self.repo.get_by_id(notification_id)
        if not notification:
            raise NotificationNotFoundException(str(notification_id))
        return {"status": notification.processing_status}