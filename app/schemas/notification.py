from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class NotificationCreate(BaseModel):
    user_id: UUID
    title: str
    text: str

class NotificationRead(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    text: str
    created_at: datetime
    read_at: datetime | None
    category: str | None
    confidence: float | None
    processing_status: str

    class Config:
        from_attributes = True