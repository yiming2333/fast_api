"""pytest 共享 fixtures —— 同步 TestClient + SQLite 覆盖。

策略：
- 普通演示路由测试（不碰 DB）→ 用 `client`，session 级别
- SQLAlchemy CRUD 测试      → 用 `db_client`，每个 function 独立的 SQLite 内存库
                              避免测试间数据污染

db_client 内部：
1. 创建 aiosqlite 引擎 + async_sessionmaker
2. 通过 dependency_overrides 替换 get_db
3. 在 asyncio 事件循环里 create_all + seed 默认用户
4. 测试结束后 dispose
"""

import asyncio
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app


# ---------------------------------------------------------------------------
# 普通 client（session 级别，不 override DB —— 走应用默认 MySQL 连接配置）
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def client() -> TestClient:
    """整个测试会话复用同一个 TestClient 实例（非 DB 路由测试用）。"""
    return TestClient(app)


@pytest.fixture
def alice_token(db_client: TestClient) -> str:
    """登录示例用户 alice（密码 secret），返回 access_token。

    依赖 db_client fixture，确保在有 alice 种子用户的测试库中执行。
    """
    resp = db_client.post(
        "/api/v1/auth/token",
        data={"username": "alice", "password": "secret"},
    )
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(alice_token: str) -> dict:
    """携带 Bearer token 的请求头。"""
    return {"Authorization": f"Bearer {alice_token}"}


# ---------------------------------------------------------------------------
# DB client（每个 function 独立 SQLite 内存库）
# ---------------------------------------------------------------------------
@pytest.fixture
def db_client() -> TestClient:
    """SQLAlchemy CRUD 测试用的 TestClient。

    内部通过 dependency_overrides 把 get_db 替换为 aiosqlite 内存库，
    所以：
    - 不依赖真实 MySQL
    - 每个测试独立的干净库
    - create_all + seed 默认用户在 async 事件循环里同步执行
    """
    # SQLite 内存库 URL（aiosqlite）
    db_url = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(db_url, echo=False)
    session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # ---- 覆盖 get_db ----
    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    # 注意：TestClient 实例要在 override 之后创建
    # （否则 lifespan 里的 init_db 会先跑 MySQL）
    app.dependency_overrides[get_db] = _get_db

    # ---- 创建表 + 种子数据（需要 asyncio 事件循环）----
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_create_tables(engine))
        loop.run_until_complete(_seed_test_user(session_maker))
    finally:
        loop.close()

    # ---- 创建 TestClient（with lifespan 上下文）----
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        # 清理
        app.dependency_overrides.pop(get_db, None)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_dispose(engine))
        finally:
            loop.close()


async def _create_tables(engine) -> None:
    """建表。"""
    import app.models  # noqa: F401 —— 注册到 Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_test_user(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """在测试库中创建默认用户 alice。"""
    from app.core.security import get_password_hash
    from app.models.user import UserORM

    async with session_maker() as session:
        user = UserORM(
            username="alice",
            email="alice@example.com",
            full_name="Alice Wonderson",
            hashed_password=get_password_hash("secret"),
            disabled=False,
        )
        session.add(user)
        await session.commit()


async def _dispose(engine) -> None:
    await engine.dispose()
