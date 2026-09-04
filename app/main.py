"""应用入口。

职责清晰：创建应用、注册中间件/异常/路由、挂载静态与模板、
管理数据库连接池生命周期（startup 初始化 + shutdown 释放）。
"""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger
from app.core.middleware import register_middleware
from app.db.session import close_engine, get_db, init_db
from app.db.seed import seed_default_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：startup 建表，shutdown 释放。"""
    logger.info("应用启动：初始化数据库连接池")
    try:
        await init_db()
        logger.info("数据库表已就绪")
    except Exception as exc:
        # MySQL 连不上时只告警，不阻断应用启动
        # 这样内存字典演示路由仍然可用；真实 DB 路由调用时会返回 503
        logger.warning(
            "数据库初始化失败（应用仍可启动）: %s",
            exc,
        )

    # 创建默认用户（如果数据库可用）
    try:
        await seed_default_user()
    except Exception as exc:
        logger.warning("种子数据写入失败: %s", exc)

    try:
        yield
    finally:
        logger.info("应用关闭：释放数据库连接池")
        await close_engine()


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "开发者",
        "url": "http://example.com/contact/",
        "email": "dev@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

# 中间件与异常处理器
register_middleware(app)
register_exception_handlers(app)

# 业务路由统一挂载到 /api/v1 前缀
app.include_router(api_router, prefix=settings.api_v1_prefix)

# 静态资源与模板（应用级挂载，不在 /api/v1 之下）
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", tags=["根"], summary="健康检查")
async def read_root():
    """根路径，简单的 Hello 响应。"""
    return {"message": "Hello, FastAPI!"}


@app.get("/health", tags=["运维"], summary="健康检查（含数据库连通性）")
async def health_check(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """检查 API 与数据库连通性。

    - DB 正常 → 200 `{"status": "healthy", "checks": {"api": "ok", "db": "ok"}}`
    - DB 异常 → 503 `{"status": "unhealthy", "checks": {"api": "ok", "db": "error"}}`

    供 Docker HEALTHCHECK 与负载均衡探针使用。
    """
    checks = {"api": "ok"}
    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        logger.warning("健康检查 DB 探测失败: %s", exc)
        checks["db"] = "error"
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "checks": checks},
        )
    return {"status": "healthy", "checks": checks}


@app.get("/hello/{name}", response_class=HTMLResponse, tags=["页面"], summary="Jinja2 模板示例")
async def hello(request: Request, name: str):
    """渲染 Jinja2 模板。"""
    return templates.TemplateResponse(
        request=request,
        name="hello.html",
        context={"name": name},
    )
