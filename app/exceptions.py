from fastapi import HTTPException
from typing import Any, Dict, Optional

class NotificationServiceException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class NotificationNotFoundException(NotificationServiceException):
    def __init__(self, notification_id: str):
        super().__init__(
            status_code=404,
            detail=f"Уведомление с ID {notification_id} не найдено"
        )

class RateLimitExceededException(NotificationServiceException):
    def __init__(self):
        super().__init__(
            status_code=429,
            detail="Превышен лимит запросов. Пожалуйста, повторите попытку позже."
        )

class DatabaseConnectionException(NotificationServiceException):
    def __init__(self, detail: str = "Ошибка подключения к базе данных"):
        super().__init__(
            status_code=503,
            detail=detail
        )