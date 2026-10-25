from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.content import router as content_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(content_router)
