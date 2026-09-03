"""自定义中间件。

中间件按注册顺序执行：请求正序、响应反序。
将业务无关的横切逻辑（日志、计时、压缩、CORS）从路由代码中剥离。
"""

import time

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import settings
from .logging import logger


async def log_requests(request: Request, call_next):
    """记录每个请求的方法、URL、状态码与耗时。"""
    logger.info("请求: %s %s", request.method, request.url)
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        "响应: %s %s 状态码=%s 耗时=%.3fs",
        request.method,
        request.url,
        response.status_code,
        process_time,
    )
    return response


async def add_process_time_header(request: Request, call_next):
    """在响应头中追加 X-Process-Time（毫秒）。"""
    start_time = time.time()
    response = await call_next(request)
    process_time = int((time.time() - start_time) * 1000)
    response.headers["X-Process-Time"] = str(process_time)
    return response


def register_middleware(app) -> None:
    """集中注册所有中间件。

    顺序很重要：先注册的中间件位于最外层。
    这里 GZip 在最外（压缩所有响应），CORS 次之，自定义日志/计时最内。
    """
    # 当响应大小超过 1000 字节时自动压缩
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(add_process_time_header)
    app.middleware("http")(log_requests)
