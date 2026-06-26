from fastapi import APIRouter
from src.api.v1.endpoints import assets, relationships

api_router = APIRouter()
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(relationships.router, prefix="/relationships", tags=["relationships"])
