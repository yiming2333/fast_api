"""数据访问层：SQLAlchemy 异步引擎与会话。

设计要点：
- 只暴露一个 get_db() 入口，职责单一：提供 AsyncSession 并保证 close
- 事务边界由调用侧控制（CRUD 函数内显式 commit/rollback）
- 引擎采用延迟初始化（lazy），便于测试时通过 dependency_overrides
  替换为 SQLite 内存数据库（无需真实 MySQL 即可跑通全部测试）
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ---------------------------------------------------------------------------
# ORM 基类
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """所有 ORM 模型的公共基类。"""


# ---------------------------------------------------------------------------
# 引擎 / 会话工厂 —— 延迟初始化
# ---------------------------------------------------------------------------
_engine = None
_session_maker = None


def get_engine(url: str | None = None):
    """获取（或首次创建）异步引擎。

    Args:
        url: 显式传入 URL 时，用它创建引擎（测试替换时使用）；
             否则从 settings.get_db_url() 读取。
    """
    global _engine, _session_maker
    if url is None:
        url = settings.get_db_url()

    # 已有引擎且 URL 相同则复用（避免模块级重建）
    if _engine is not None and str(_engine.url) == url:
        return _engine

    # SQLAlchemy 2.0 create_async_engine
    # MySQL 驱动 aiomysql 支持 1000 连接池上限 + 20 溢出
    _engine = create_async_engine(
        url,
        echo=settings.debug,
        pool_pre_ping=True,
        future=True,
        connect_args={
            # MySQL 相关 connect_args 仅对 aiomysql 有意义；
            # SQLite/aio 会忽略多余字段
            "charset": "utf8mb4",
        } if "mysql" in url else {},
    )
    _session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,  # 提交后对象不自动过期，便于直接返回给 Pydantic
    )
    return _engine


def get_session_maker(url: str | None = None) -> async_sessionmaker[AsyncSession]:
    """返回 async_sessionmaker（首次调用会创建引擎）。"""
    get_engine(url)
    return _session_maker  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# FastAPI 依赖：提供 AsyncSession
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """提供一个 AsyncSession，请求结束后自动关闭。

    事务边界由调用侧决定：
      - 只读：直接 session.execute(select(...)) 即可，不开启 ORM 事务
      - 写操作：session.add() / session.execute() 后显式 await session.commit()
                异常时 await session.rollback()

    这个 yield 形式的依赖是 FastAPI 推荐做法：
      try: yield session   → 业务代码
      finally: await session.close()  → 清理
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


# ---------------------------------------------------------------------------
# 启动时建表
# ---------------------------------------------------------------------------
async def init_db(url: str | None = None) -> None:
    """导入所有 ORM 模型后，执行 Base.metadata.create_all。

    必须在调用前先 import app.models.*，否则 Base.metadata 是空的。
    这里动态导入以避免循环依赖。
    """
    import app.models  # noqa: F401 —— 注册所有模型到 Base.metadata

    engine = get_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_engine() -> None:
    """应用关闭时释放连接池。"""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_maker = None


AsyncSessionDep = Depends(get_db)  # noqa: E501 — 便捷别名，方便 router 写 Depends(get_db)
