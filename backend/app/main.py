"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.response import ok
from app.api import api_router

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(api_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    """健康检查"""
    # TODO: 检查 DB / Redis / OBS / Meilisearch 连接状态
    return ok({
        "status": "ok",
        "version": "0.1.0",
    })
