"""用户路由测试：列表、创建、当前登录用户、鉴权失败。"""

from fastapi.testclient import TestClient


def test_list_users(client: TestClient):
    resp = client.get("/api/v1/users/")
    assert resp.status_code == 200
    assert resp.json() == [{"username": "Rick"}, {"username": "Morty"}]


def test_create_user_password_not_in_response(client: TestClient):
    """响应模型 UserOut 不应包含 password 字段。"""
    payload = {
        "username": "newbie",
        "email": "newbie@example.com",
        "full_name": "New Bie",
        "password": "super-secret",
    }
    resp = client.post("/api/v1/users/", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert body["username"] == "newbie"
    assert "password" not in body


def test_create_user_invalid_email(client: TestClient):
    """email 格式不合法应 422。"""
    resp = client.post(
        "/api/v1/users/",
        json={"username": "x", "email": "not-an-email", "password": "p"},
    )
    assert resp.status_code == 422


def test_me_requires_auth(client: TestClient):
    """未携带 token 访问 /users/me 应 401。"""
    assert client.get("/api/v1/users/me").status_code == 401


def test_me_with_valid_token(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert "hashed_password" not in body


def test_me_items_with_valid_token(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/users/me/items", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == [{"item_id": "Foo", "owner": "alice"}]


def test_me_with_invalid_token(client: TestClient):
    """伪造 token 应 401。"""
    resp = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert resp.status_code == 401
