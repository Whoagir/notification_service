from fastapi import APIRouter, Depends, Query, Request, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.schemas.notification import NotificationCreate, NotificationRead
from app.config.database import get_session
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService
from fastapi_cache.decorator import cache
from app.utils.cache import custom_key_builder

router = APIRouter(tags=["notifications"])

@router.get(
    "/",
    response_model=list[NotificationRead],
    summary="Получить список уведомлений",
    description="Возвращает список уведомлений для указанного пользователя с поддержкой пагинации",
    response_description="Список объектов уведомлений",
)
@cache(expire=60, namespace="notifications", key_builder=custom_key_builder)
async def get_notifications(
    request: Request,
    user_id: UUID = Query(..., description="ID пользователя"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(10, ge=1, le=100, description="Максимальное количество возвращаемых записей"),
    db: AsyncSession = Depends(get_session),
):
    repo = NotificationRepository(db)
    service = NotificationService(repo)
    notifications = await service.get_notifications(user_id, skip, limit)
    return notifications

@router.get(
    "/{notification_id}",
    response_model=NotificationRead,
    summary="Получить детальную информацию об уведомлении",
    description="Возвращает полную информацию о конкретном уведомлении по его ID",
    response_description="Объект уведомления",
)
async def get_notification(
    notification_id: UUID = Path(..., description="ID уведомления"),
    db: AsyncSession = Depends(get_session),
):
    repo = NotificationRepository(db)
    service = NotificationService(repo)
    return await service.get_notification(notification_id)

@router.post(
    "/",
    response_model=NotificationRead,
    summary="Создать новое уведомление",
    description="Создает новое уведомление и отправляет его текст на анализ в AI API асинхронно",
    response_description="Созданное уведомление",
)
async def create_notification(
    notification: NotificationCreate = Body(..., description="Данные для создания уведомления"),
    db: AsyncSession = Depends(get_session),
):
    repo = NotificationRepository(db)
    service = NotificationService(repo)
    return await service.create_notification(notification)

@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="Отметить уведомление как прочитанное",
    description="Обновляет статус уведомления на 'прочитанное' и устанавливает время прочтения",
    response_description="Обновленное уведомление",
)
async def mark_notification_as_read(
    notification_id: UUID = Path(..., description="ID уведомления"),
    db: AsyncSession = Depends(get_session),
):
    repo = NotificationRepository(db)
    service = NotificationService(repo)
    return await service.mark_as_read(notification_id)

@router.get(
    "/{notification_id}/status",
    response_model=dict,
    summary="Получить статус обработки уведомления",
    description="Возвращает текущий статус обработки уведомления (pending, processing, completed, failed)",
    response_description="Статус обработки",
)
async def get_notification_status(
    notification_id: UUID = Path(..., description="ID уведомления"),
    db: AsyncSession = Depends(get_session),
):
    repo = NotificationRepository(db)
    service = NotificationService(repo)
    return await service.get_status(notification_id)