from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.notification import Notification
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, notification_id: UUID) -> Optional[Notification]:
        """Получить уведомление по ID"""
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalars().first()

    async def get_list(self, user_id: UUID, last_created_at: datetime | None, limit: int) -> List[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if last_created_at:
            query = query.where(Notification.created_at < last_created_at)
        query = query.order_by(Notification.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def update(self, notification: Notification) -> Notification:
        await self.db.flush()
        return notification