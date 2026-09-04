"""pytest 共享 fixtures —— TestClient + SQLite 覆盖（pytest-asyncio 异步 fixture）。

策略：
- `client`（session 级）：整个会话复用同一 TestClient + SQLite 内存库，
  供非 DB 路由测试使用；同时 override get_db，避免 lifespan 连真实 MySQL，
  并让 /health 等使用 Depends(get_db) 的端点可用。
- `db_client`（function 级）：每个测试独立的 SQLite 内存库，
  供 SQLAlchemy CRUD 测试使用，避免测试间数据污染。

两个 fixture 都通过 dependency_overrides 把 get_db 替换为 aiosqlite 内存库：
- 不依赖真实 MySQL
- 每个测试独立的干净库（db_client）或会话级共享库（client）

db_client 依赖 client（确保 session 级 override 已就位），临时替换为本测试
专属的干净库，结束后恢复 client 的 override。
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
async def _create_tables(engine) -> None:
    """建表：先注册所有 ORM 模型到 Base.metadata，再 create_all。"""
    import app.models  # noqa: F401 —— 注册所有模型

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_test_user(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """在测试库中创建默认用户 alice（密码 secret）。"""
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


def _make_get_db(session_maker: async_sessionmaker[AsyncSession]):
    """构造一个替换 get_db 的 async 生成器依赖。"""

    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    return _get_db


# ---------------------------------------------------------------------------
# client（session 级 —— 整个测试会话复用同一 TestClient + SQLite）
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[TestClient, None]:
    """session 级 TestClient，get_db override 为 SQLite 内存库。

    供非 DB 路由测试（test_main / test_examples / test_files / test_forms）
    使用，同时让 /health 端点可正常检查 DB 连通性。
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    app.dependency_overrides[get_db] = _make_get_db(session_maker)
    await _create_tables(engine)
    await _seed_test_user(session_maker)

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


# ---------------------------------------------------------------------------
# db_client（function 级 —— 每个测试独立的 SQLite 内存库）
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_client(client: TestClient) -> AsyncGenerator[TestClient, None]:
    """function 级 TestClient，每个测试独立的 SQLite 内存库。

    依赖 `client`（session 级，确保 override 机制已就位），然后临时替换为
    本测试专属的干净库，结束后恢复 `client` 的 override。
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 保存 session 级 client 的 override，测试结束后恢复
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _make_get_db(session_maker)
    await _create_tables(engine)
    await _seed_test_user(session_maker)

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        if previous is not None:
            app.dependency_overrides[get_db] = previous
        else:
            app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


# ---------------------------------------------------------------------------
# 认证 fixtures（依赖 db_client，确保 alice 种子用户存在）
# ---------------------------------------------------------------------------
@pytest.fixture
def alice_token(db_client: TestClient) -> str:
    """登录示例用户 alice（密码 secret），返回 access_token。"""
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
