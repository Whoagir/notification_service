from fastapi import APIRouter
from app.api.v1.endpoints import notifications

router = APIRouter()
router.include_router(notifications.router, prefix="/notifications")