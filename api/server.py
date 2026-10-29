import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import config as config_router
from api.routes import task as task_router
from api.routes import history as history_router

app = FastAPI(title="Douyin Downloader API")

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ... (middlewares and routers) ...

app.include_router(config_router.router, prefix="/api/config", tags=["Config"])
app.include_router(task_router.router, prefix="/api/task", tags=["Task"])
app.include_router(history_router.router, prefix="/api/history", tags=["History"])

import sys

# 挂载前端静态文件 (生产环境运行桌面端时使用)
frontend_dist = None
if getattr(sys, 'frozen', False):
    # PyInstaller 环境下的多种可能路径探测
    search_paths = [
        Path(sys.executable).parent / "_internal" / "web" / "dist",  # v6 onedir
        Path(sys.executable).parent / "web" / "dist",                # custom copy
        Path(sys._MEIPASS) / "web" / "dist"                          # standard fallback
    ]
    for p in search_paths:
        if p.exists():
            frontend_dist = p
            break
else:
    # 开发环境下
    frontend_dist = Path(__file__).parent.parent / "web" / "dist"

if frontend_dist and frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_dist / "index.html"))


if __name__ == "__main__":
    uvicorn.run("api.server:app", host="127.0.0.1", port=23851, reload=True)
