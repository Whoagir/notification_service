import pytest
import pytest_asyncio
import uuid
import json
import random
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from fastapi import FastAPI

from app.main import app, startup
from app.config.database import get_session, Base
from app.models.notification import Notification
from app.celery_app import celery_app
from app.tasks import analyze_text

# Создаем тестовую базу данных
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Создаем тестовый движок и сессию
test_engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


# Фикстура для настройки и очистки тестовой базы данных
@pytest_asyncio.fixture(scope="function")
async def setup_database():
    # Создаем таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Выполняем тесты
    yield

    # Удаляем таблицы после тестов
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Фикстура для получения тестовой сессии БД
@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


# Переопределяем зависимость get_session для тестов
@pytest.fixture
def override_get_session(db_session):
    async def _get_session():
        yield db_session

    app.dependency_overrides[get_session] = _get_session
    yield
    app.dependency_overrides.clear()


# Фикстура для асинхронного клиента
@pytest_asyncio.fixture
async def async_client(override_get_session):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Фикстура для синхронного клиента
@pytest.fixture
def test_client(override_get_session):
    with TestClient(app) as client:
        yield client


# Мокируем Redis и Celery
@pytest.fixture(autouse=True)
def mock_redis_and_celery():
    # Мокируем Redis
    with patch("app.main.aioredis.from_url") as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping.return_value = True
        mock_redis.return_value = mock_redis_instance

        # Мокируем Celery
        with patch("app.services.notification_service.celery_app") as mock_celery:
            mock_celery.send_task.return_value = MagicMock()
            yield


# Тест для функции analyze_text
def test_analyze_text():
    # Тест для критического текста
    critical_text = "Error occurred in the system"
    result = analyze_text(critical_text)
    assert result["category"] == "critical"
    assert 0.7 <= result["confidence"] <= 0.95

    # Тест для предупреждающего текста
    warning_text = "Warning: disk space is low"
    result = analyze_text(warning_text)
    assert result["category"] == "warning"
    assert 0.6 <= result["confidence"] <= 0.9

    # Тест для информационного текста
    info_text = "System started successfully"
    result = analyze_text(info_text)
    assert result["category"] == "info"
    assert 0.8 <= result["confidence"] <= 0.99


# Тест для создания уведомления
@pytest.mark.asyncio
async def test_create_notification(async_client, setup_database):
    user_id = str(uuid.uuid4())
    response = await async_client.post(
        "/api/v1/notifications/",
        json={"user_id": user_id, "title": "Test Notification", "text": "Error happened"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["title"] == "Test Notification"
    assert data["text"] == "Error happened"
    assert data["processing_status"] == "pending"
    assert "id" in data


# Тест для получения списка уведомлений
@pytest.mark.asyncio
async def test_get_notifications(async_client, db_session, setup_database):
    # Создаем тестовые данные
    user_id = uuid.uuid4()
    notifications = []

    for i in range(3):
        notification = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            title=f"Test Notification {i}",
            text=f"Test text {i}",
            created_at=datetime.utcnow(),
            processing_status="completed",
            category="info",
            confidence=0.9
        )
        db_session.add(notification)
        notifications.append(notification)

    await db_session.commit()

    # Патчим FastAPICache.get_backend().get и get_with_ttl
    with patch('fastapi_cache.FastAPICache.get_backend') as mock_get_backend:
        backend = AsyncMock()
        backend.get = AsyncMock(return_value=None)
        backend.get_with_ttl = AsyncMock(return_value=(None, None))
        mock_get_backend.return_value = backend

        # Получаем уведомления через API
        response = await async_client.get(
            f"/api/v1/notifications/?user_id={user_id}&skip=0&limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    # Проверяем пагинацию с новым патчем
    with patch('fastapi_cache.FastAPICache.get_backend') as mock_get_backend:
        backend = AsyncMock()
        backend.get = AsyncMock(return_value=None)
        backend.get_with_ttl = AsyncMock(return_value=(None, None))
        mock_get_backend.return_value = backend

        response = await async_client.get(
            f"/api/v1/notifications/?user_id={user_id}&skip=1&limit=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Notification 1"


# Тест для получения детальной информации об уведомлении
@pytest.mark.asyncio
async def test_get_notification(async_client, db_session, setup_database):
    # Создаем тестовое уведомление
    user_id = uuid.uuid4()
    notification_id = uuid.uuid4()

    notification = Notification(
        id=notification_id,
        user_id=user_id,
        title="Test Notification",
        text="Test text",
        created_at=datetime.utcnow(),
        processing_status="completed",
        category="info",
        confidence=0.9
    )

    db_session.add(notification)
    await db_session.commit()

    # Получаем уведомление через API
    response = await async_client.get(f"/api/v1/notifications/{notification_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(notification_id)
    assert data["title"] == "Test Notification"
    assert data["processing_status"] == "completed"


# Тест для отметки уведомления как прочитанного
@pytest.mark.asyncio
async def test_mark_notification_as_read(async_client, db_session, setup_database):
    # Создаем тестовое уведомление
    user_id = uuid.uuid4()
    notification_id = uuid.uuid4()

    notification = Notification(
        id=notification_id,
        user_id=user_id,
        title="Test Notification",
        text="Test text",
        created_at=datetime.utcnow(),
        processing_status="completed",
        category="info",
        confidence=0.9,
        read_at=None
    )

    db_session.add(notification)
    await db_session.commit()

    # Отмечаем как прочитанное через API
    response = await async_client.patch(f"/api/v1/notifications/{notification_id}/read")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(notification_id)
    assert data["read_at"] is not None


# Тест для проверки статуса обработки уведомления
@pytest.mark.asyncio
async def test_get_notification_status(async_client, db_session, setup_database):
    # Создаем тестовое уведомление
    user_id = uuid.uuid4()
    notification_id = uuid.uuid4()

    notification = Notification(
        id=notification_id,
        user_id=user_id,
        title="Test Notification",
        text="Test text",
        created_at=datetime.utcnow(),
        processing_status="processing",
        category=None,
        confidence=None
    )

    db_session.add(notification)
    await db_session.commit()

    # Получаем статус через API
    response = await async_client.get(f"/api/v1/notifications/{notification_id}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"


# Тест для обработки ошибки при получении несуществующего уведомления
@pytest.mark.asyncio
async def test_get_nonexistent_notification(async_client, setup_database):
    notification_id = uuid.uuid4()
    response = await async_client.get(f"/api/v1/notifications/{notification_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Уведомление не найдено"


# Тест для валидации входных данных
@pytest.mark.asyncio
async def test_create_notification_validation(async_client, setup_database):
    # Отсутствует обязательное поле
    response = await async_client.post(
        "/api/v1/notifications/",
        json={"title": "Test Notification", "text": "Error happened"}
    )

    assert response.status_code == 422

    # Неверный формат UUID
    response = await async_client.post(
        "/api/v1/notifications/",
        json={"user_id": "not-a-uuid", "title": "Test Notification", "text": "Error happened"}
    )

    assert response.status_code == 422


# Тест для кэширования
@pytest.mark.asyncio
async def test_notifications_caching(async_client, db_session, setup_database):
    # Создаем тестовые данные
    user_id = uuid.uuid4()
    notification = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Test Notification",
        text="Test text",
        created_at=datetime.utcnow(),
        processing_status="completed",
        category="info",
        confidence=0.9
    )

    db_session.add(notification)
    await db_session.commit()

    # Первый запрос (данные из БД)
    with patch('fastapi_cache.FastAPICache.get_backend') as mock_get_backend:
        backend = AsyncMock()
        backend.get = AsyncMock(return_value=None)
        backend.get_with_ttl = AsyncMock(return_value=(None, None))
        backend.set = AsyncMock()
        mock_get_backend.return_value = backend

        response = await async_client.get(
            f"/api/v1/notifications/?user_id={user_id}&skip=0&limit=10"
        )

        assert response.status_code == 200

        # Проверяем, что кэш был установлен
        backend.set.assert_called_once()

    # Второй запрос (должен использовать кэш)
    # Вместо списка используем строку JSON, которая хешируема
    cached_data = json.dumps([{
        "id": str(notification.id),
        "user_id": str(user_id),
        "title": "Test Notification",
        "text": "Test text",
        "created_at": notification.created_at.isoformat(),
        "read_at": None,
        "category": "info",
        "confidence": 0.9,
        "processing_status": "completed"
    }])

    with patch('fastapi_cache.FastAPICache.get_backend') as mock_get_backend:
        backend = AsyncMock()
        backend.get = AsyncMock(return_value=None)
        # Возвращаем кэшированные данные как строку
        backend.get_with_ttl = AsyncMock(return_value=(60, cached_data))
        mock_get_backend.return_value = backend

        # Патчим декодирование кэша, чтобы оно возвращало правильный объект
        with patch('fastapi_cache.coder.JsonCoder.decode', return_value=json.loads(cached_data)):
            response = await async_client.get(
                f"/api/v1/notifications/?user_id={user_id}&skip=0&limit=10"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == str(notification.id)


# Тест для startup события
@pytest.mark.asyncio
async def test_startup_event():
    with patch("app.main.aioredis.from_url") as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping.return_value = True
        mock_redis.return_value = mock_redis_instance

        with patch("app.main.FastAPICache") as mock_cache:
            await startup()
            mock_redis.assert_called_once()
            mock_cache.init.assert_called_once()


# Тест для обработки исключений
@pytest.mark.asyncio
async def test_exception_handlers(async_client, setup_database):
    # Тест для ValidationError
    response = await async_client.post(
        "/api/v1/notifications/",
        json={"invalid_field": "value"}
    )

    assert response.status_code == 422

    # Проверяем, что обработчик исключений настроен
    assert Exception in app.exception_handlers