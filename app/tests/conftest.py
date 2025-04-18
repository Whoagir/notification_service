import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend


@pytest.fixture(autouse=True)
async def init_cache():
    # Создаём AsyncMock для redis
    redis = AsyncMock()

    # Настраиваем методы redis
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.ttl = AsyncMock(return_value=60)
    redis.ping = AsyncMock(return_value=True)

    # Настраиваем pipeline
    pipeline = AsyncMock()
    pipeline.__aenter__ = AsyncMock(return_value=pipeline)
    pipeline.__aexit__ = AsyncMock(return_value=False)
    pipeline.execute = AsyncMock(return_value=[60, None])  # ttl и get результаты
    pipeline.ttl = AsyncMock(return_value=pipeline)
    pipeline.get = AsyncMock(return_value=pipeline)

    redis.pipeline = MagicMock(return_value=pipeline)

    # Создаем бэкенд и мокируем его методы
    backend = RedisBackend(redis)
    backend.get = AsyncMock(return_value=None)
    backend.get_with_ttl = AsyncMock(return_value=(60, None))

    # Патчим FastAPICache
    with patch('fastapi_cache.FastAPICache.get_backend', return_value=backend):
        # Инициализируем FastAPICache
        FastAPICache.init(backend, prefix="test-prefix")

        yield

        # Очищаем кэш после теста (используем AsyncMock)
        clear_mock = AsyncMock()
        with patch('fastapi_cache.FastAPICache.clear', clear_mock):
            await FastAPICache.clear()