from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import AsyncGenerator
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:12345@localhost:5432/notification_service_db")

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=20,  # Максимальное количество соединений в пуле
    max_overflow=10,  # Дополнительные соединения при перегрузке
    pool_recycle=1800,  # Перезапуск соединений каждые 30 минут
    pool_pre_ping=True  # Проверка соединения перед использованием
)
Base = declarative_base()

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        async with session.begin():
            yield session