from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.api.v1.router import router as router_v1
from app.config.logging_config import setup_logging
from app.middlewares.rate_limit import RateLimitMiddleware
from app.exceptions import NotificationNotFoundException, RateLimitExceededException, DatabaseConnectionException
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
import os
from dotenv import load_dotenv
import logging
from prometheus_fastapi_instrumentator import Instrumentator
from app.utils.cache import custom_key_builder

load_dotenv()

app = FastAPI(
    title="Notification Service API",
    description="API для управления уведомлениями пользователей",
    version="1.0.0",
    openapi_version="3.0.2",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Настройка Prometheus
Instrumentator().instrument(app).expose(app)

# Добавляем middleware
app.add_middleware(RateLimitMiddleware, rate_limit_per_minute=60)

# Подключаем роутер версии v1
app.include_router(router_v1, prefix="/api/v1")

logger = logging.getLogger("app")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@3/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@next/bundles/redoc.standalone.js",
    )

@app.on_event("startup")
async def startup():
    setup_logging()
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        logger.info(f"Попытка подключения к Redis: {redis_url}")
        redis = aioredis.from_url(redis_url, encoding="utf8")
        await redis.ping()
        logger.info("Успешное подключение к Redis")
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
        logger.info("FastAPICache инициализирован")
    except Exception as e:
        logger.info(f"Ошибка инициализации Redis: {e}")

# def custom_key_builder(
#     func,
#     namespace: str = "",
#     request: Request = None,
#     response=None,
#     *args,
#     **kwargs
# ):
#     prefix = FastAPICache.get_prefix()
#     query_params = request.query_params if request else {}
#     user_id = str(query_params.get("user_id", ""))
#     last_created_at = query_params.get("last_created_at", "none")
#     limit = str(query_params.get("limit", "10"))
#
#     if last_created_at != "none":
#         try:
#             last_created_at = datetime.datetime.fromisoformat(last_created_at).isoformat()
#         except ValueError:
#             last_created_at = "invalid"
#
#     cache_key = f"{prefix}:{namespace}:{func.__module__}:{func.__name__}:{user_id}:{last_created_at}:{limit}"
#     logger.info(f"Сформирован ключ кэша: {cache_key}")
#     return cache_key

@app.exception_handler(NotificationNotFoundException)
async def notification_not_found_handler(request: Request, exc: NotificationNotFoundException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RateLimitExceededException)
async def rate_limit_handler(request: Request, exc: RateLimitExceededException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(DatabaseConnectionException)
async def database_connection_handler(request: Request, exc: DatabaseConnectionException):
    logger.error(f"Database connection error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"},
    )