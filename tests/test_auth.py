"""认证路由测试：登录、令牌校验、凭据错误处理。"""

from fastapi.testclient import TestClient


def test_login_success(client: TestClient):
    """正确用户名密码换取 JWT。"""
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "alice", "password": "secret"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2  # JWT 三段式


def test_login_wrong_password(client: TestClient):
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "alice", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_login_unknown_user(client: TestClient):
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "nobody", "password": "whatever"},
    )
    assert resp.status_code == 401


def test_login_requires_form_data(client: TestClient):
    """OAuth2PasswordRequestForm 必须以表单形式提交。"""
    resp = client.post(
        "/api/v1/auth/token",
        json={"username": "alice", "password": "secret"},
    )
    # 表单字段缺失 -> 422
    assert resp.status_code == 422


def test_token_carries_username_claim(client: TestClient):
    """JWT payload 中 sub 应为用户名。"""
    from jose import jwt

    from app.core.config import settings

    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "alice", "password": "secret"},
    )
    token = resp.json()["access_token"]
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == "alice"
    assert "exp" in payload
