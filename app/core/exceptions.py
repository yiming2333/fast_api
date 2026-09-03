"""自定义异常与全局异常处理器。

将异常类与处理器集中管理，便于在 main.py 中统一注册，
也便于单测覆盖。
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class UnicornException(Exception):
    """业务自定义异常示例。"""

    def __init__(self, name: str):
        self.name = name


async def unicorn_exception_handler(request: Request, exc: UnicornException) -> JSONResponse:
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something wrong"},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """覆盖默认 HTTPException 响应格式，统一错误结构。

    注意：必须保留 exc.headers（如 WWW-Authenticate、X-Error），
    否则像 401 响应里的鉴权提示头会丢失，影响客户端按规范重试。
    """
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": f"HTTP error: {exc.detail}"},
        headers=headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """覆盖请求体校验错误响应，统一错误结构。"""
    return JSONResponse(
        status_code=422,
        content={"error": "数据校验失败", "details": exc.errors()},
    )


def register_exception_handlers(app) -> None:
    """集中注册所有异常处理器。"""
    app.add_exception_handler(UnicornException, unicorn_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
