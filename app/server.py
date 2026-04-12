# app/server.py
"""FastAPI Web 服务器入口。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.main import build_app
from app.websocket_handler import WebSocketSession

LOGGER = logging.getLogger("podcast.server")

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

# 全局 app 实例
_app_context: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时初始化
    LOGGER.info("Initializing DeepTalk server...")
    _app_context["app"] = build_app()
    LOGGER.info("DeepTalk server ready")
    yield
    # 关闭时清理
    _app_context.clear()


# 创建 FastAPI 应用
server = FastAPI(
    title="DeepTalk Agent",
    description="语音对话 AI 助手",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
# 注意：生产环境应指定具体域名并启用 allow_credentials
server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_methods=["*"],
    allow_headers=["*"],
)


# API 路由必须在静态文件挂载之前
@server.get("/health")
async def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok"}


@server.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket 主入口。"""
    app = _app_context.get("app")
    if not app:
        await websocket.close(code=1011, reason="Server not ready")
        return

    session = WebSocketSession(
        websocket=websocket,
        state_machine=app["state_machine"],
        memory=app["memory"],
        asr=app["asr"],
        agent=app["agent"],
        tts=app["tts"],
        audio_out=app["audio_out"],
        audio_sample_rate=app["config"].audio_sample_rate,
    )
    await session.run()


@server.get("/api/config")
async def get_config() -> dict[str, str]:
    """获取当前配置信息。"""
    app = _app_context.get("app")
    if not app:
        raise HTTPException(status_code=503, detail="Server not ready")
    return {
        "asr_provider": app["asr_provider"],
        "tts_provider": app["tts_provider"],
        "llm_model": app["llm_provider"],
    }


# 生产模式：托管前端静态文件
if FRONTEND_DIST.exists():
    # 挂载静态资源目录
    server.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @server.get("/", response_model=None)
    async def index() -> FileResponse:
        """返回前端页面。"""
        return FileResponse(FRONTEND_DIST / "index.html", media_type="text/html")

    # SPA 路由回退
    @server.get("/{path:path}", response_model=None)
    async def spa_fallback(path: str) -> FileResponse | dict[str, str]:
        """SPA 路由回退。"""
        # 检查是否是静态文件
        file_path = FRONTEND_DIST / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # 否则返回 index.html（SPA 路由）
        return FileResponse(FRONTEND_DIST / "index.html", media_type="text/html")
else:
    @server.get("/", response_model=None)
    async def index() -> dict[str, str]:
        """返回 API 信息。"""
        return {"message": "DeepTalk Agent API", "docs": "/docs"}


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    """启动服务器。"""
    import uvicorn
    uvicorn.run(server, host=host, port=port)


if __name__ == "__main__":
    run_server()
