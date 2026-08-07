"""API 路由聚合"""
from fastapi import APIRouter

from app.api.endpoints import assets, tags, upload, search, collect, auth, users, review, import_api

api_router = APIRouter()

api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(collect.router, prefix="/collect", tags=["collect"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(import_api.router, prefix="/import", tags=["import"])
