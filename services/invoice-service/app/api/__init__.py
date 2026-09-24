from fastapi import APIRouter

from app.api import uploads

# Feature routers are included here and mounted under settings.api_prefix.
api_router = APIRouter()
api_router.include_router(uploads.router)
