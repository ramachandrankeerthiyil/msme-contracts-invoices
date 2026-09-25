from fastapi import APIRouter

from app.api import contracts, uploads

# Feature routers, each mounted under settings.api_prefix by create_app(), so the list lives at
# `/api/contracts` itself. `uploads` comes first: its `/uploads` route must win over `/{id}`.
api_routers: list[APIRouter] = [uploads.router, contracts.router]
