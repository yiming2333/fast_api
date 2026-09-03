"""pytest 共享 fixtures。

集中提供 TestClient 与已登录用户的 Authorization 头，
避免每个测试文件重复样板代码。
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """整个测试会话复用同一个 TestClient 实例。"""
    return TestClient(app)


@pytest.fixture(scope="session")
def alice_token(client: TestClient) -> str:
    """登录示例用户 alice（密码 secret），返回 access_token。

    使用 session 级别：JWT 在测试会话内有效，避免重复登录开销。
    """
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "alice", "password": "secret"},
    )
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(alice_token: str) -> dict:
    """携带 Bearer token 的请求头，直接传给 client 的 headers 参数。"""
    return {"Authorization": f"Bearer {alice_token}"}
