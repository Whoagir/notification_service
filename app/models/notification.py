from sqlalchemy import Column, String, DateTime, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from app.config.database import Base
from datetime import datetime
import uuid

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    category = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    processing_status = Column(String, default="pending")

    __table_args__ = (
        Index('idx_user_created', user_id, created_at),
        Index('idx_user_id', 'user_id'),
        Index('idx_created_at', 'created_at'),
        Index('idx_category', 'category'),
    )