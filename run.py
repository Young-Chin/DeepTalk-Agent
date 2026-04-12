#!/usr/bin/env python3
"""DeepTalk 统一启动脚本。

默认以生产模式启动，自动构建前端并从 http://localhost:8080 访问。

Usage:
    python run.py              # 生产模式（默认，后端托管前端静态文件）
    python run.py --dev        # 开发模式（前后端分离，支持热更新）
    python run.py --build      # 仅构建前端
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import signal
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
LOGGER = logging.getLogger("deeptalk.run")

# 项目根目录
ROOT_DIR = Path(__file__).parent
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

# 进程列表
processes: list[subprocess.Popen] = []


def cleanup(signum=None, frame=None):
    """清理所有子进程。"""
    LOGGER.info("Shutting down...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            p.kill()
    sys.exit(0)


def check_frontend_deps():
    """检查前端依赖是否已安装。"""
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        LOGGER.info("Installing frontend dependencies...")
        subprocess.run(
            ["npm", "install"],
            cwd=FRONTEND_DIR,
            check=True,
        )


def build_frontend():
    """构建前端。"""
    LOGGER.info("Building frontend...")
    subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        check=True,
    )
    LOGGER.info("Frontend build complete: %s", FRONTEND_DIST)


def run_dev():
    """开发模式：同时启动前后端。"""
    check_frontend_deps()

    LOGGER.info("=" * 60)
    LOGGER.info("DeepTalk 开发模式启动")
    LOGGER.info("访问地址: http://localhost:5173")
    LOGGER.info("=" * 60)
    LOGGER.info("按 Ctrl+C 停止服务")

    # 注册信号处理
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # 启动后端服务器
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "app.server"],
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": str(ROOT_DIR)},
    )
    processes.append(backend_proc)

    # 启动前端开发服务器
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
    )
    processes.append(frontend_proc)

    # 等待进程结束
    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        cleanup()


def run_prod():
    """生产模式：后端托管前端静态文件。"""
    if not FRONTEND_DIST.exists():
        LOGGER.info("Frontend not built, building now...")
        build_frontend()

    LOGGER.info("Starting DeepTalk in production mode...")
    LOGGER.info("Server: http://localhost:8080")
    LOGGER.info("")
    LOGGER.info("Press Ctrl+C to stop")

    # 注册信号处理
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # 启动后端服务器（会自动托管前端静态文件）
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "app.server"],
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": str(ROOT_DIR)},
    )
    processes.append(backend_proc)

    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="DeepTalk 统一启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run.py              生产模式（默认，访问 http://localhost:8080）
    python run.py --dev        开发模式（支持热更新，访问 http://localhost:5173）
    python run.py --build      仅构建前端
        """,
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="开发模式（前后端分离，支持热更新，前端访问 localhost:5173）",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="仅构建前端",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="后端服务器端口（默认 8080）",
    )

    args = parser.parse_args()

    if args.build:
        build_frontend()
    elif args.dev:
        run_dev()
    else:
        run_prod()


if __name__ == "__main__":
    main()
