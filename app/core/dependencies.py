"""通用依赖函数。

依赖（Dependency）用于在路由间复用逻辑：参数解析、鉴权、资源获取等。
通过 `Depends(...)` 注入，便于测试时替换为 mock。
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException


def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    """通用分页/查询参数。"""
    return {"q": q, "skip": skip, "limit": limit}


class CommonQueryParams:
    """以类形式声明的依赖（演示用）。"""

    def __init__(self, q: str | None = None, skip: int = 0, limit: int = 100):
        self.q = q
        self.skip = skip
        self.limit = limit


def query_extractor(q: str | None = None):
    """子依赖链：提取 q。"""
    return q


def query_checker(q: str = Depends(query_extractor)):
    """子依赖链：对 q 做校验。"""
    if q == "admin":
        return q + " (checked)"
    return q


async def verify_token(x_token: Annotated[str, Header()]):
    """演示：校验 X-Token 请求头。"""
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")


async def verify_api_key(x_api_key: Annotated[str, Header()]):
    """演示：校验 X-API-Key 请求头。"""
    if x_api_key != "secret-key":
        raise HTTPException(status_code=400, detail="X-API-Key invalid")


def get_db():
    """模拟数据库连接依赖（yield 模式）。

    真实场景下应替换为 SQLAlchemy 的 Session 等。
    """
    db = "database_connection"
    try:
        yield db
    finally:
        # 请求完成后清理资源
        pass


CommonDep = Annotated[dict, Depends(common_parameters)]
