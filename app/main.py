"""应用入口。

原本将路由、模型、异常处理器、中间件、静态文件、模板全部塞在
一个 600+ 行的文件中，难以维护。重构后职责清晰：

- 路由         → app/api/routers/*
- schema       → app/schemas/*
- 横切关注点   → app/core/*
- 数据访问     → app/db/*

本文件仅负责：创建应用、注册中间件/异常/路由、挂载静态与模板。
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routers import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middleware

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


@app.get("/hello/{name}", response_class=HTMLResponse, tags=["页面"], summary="Jinja2 模板示例")
async def hello(request: Request, name: str):
    """渲染 Jinja2 模板。"""
    return templates.TemplateResponse(
        request=request,
        name="hello.html",
        context={"name": name},
    )
