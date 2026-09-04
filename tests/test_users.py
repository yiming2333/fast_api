"""用户路由测试：列表、创建、当前登录用户、鉴权失败。

用户现在走真实数据库（UserORM），所以需要 db_client fixture。
"""

from fastapi.testclient import TestClient


def test_list_users(db_client: TestClient):
    """列表应包含种子用户 alice。"""
    resp = db_client.get("/api/v1/users/")
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    # 种子数据中 alice 存在
    usernames = [u["username"] for u in users]
    assert "alice" in usernames


def test_create_user_success(db_client: TestClient):
    """创建新用户，响应不含 password。"""
    payload = {
        "username": "newbie",
        "email": "newbie@example.com",
        "full_name": "New Bie",
        "password": "super-secret",
    }
    resp = db_client.post("/api/v1/users/", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "newbie"
    assert body["email"] == "newbie@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_create_user_duplicate_rejected(db_client: TestClient):
    """重复用户名应 400。"""
    payload = {
        "username": "alice",
        "email": "dup@example.com",
        "password": "pass",
    }
    resp = db_client.post("/api/v1/users/", json=payload)
    assert resp.status_code == 400
    assert "已存在" in resp.json()["detail"]


def test_create_user_invalid_email(db_client: TestClient):
    """email 格式不合法应 422。"""
    resp = db_client.post(
        "/api/v1/users/",
        json={"username": "x", "email": "not-an-email", "password": "p"},
    )
    assert resp.status_code == 422


def test_me_requires_auth(db_client: TestClient):
    """未携带 token 访问 /users/me 应 401。"""
    assert db_client.get("/api/v1/users/me").status_code == 401


def test_me_with_valid_token(db_client: TestClient, auth_headers: dict):
    resp = db_client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert "hashed_password" not in body


def test_me_items_with_valid_token(db_client: TestClient, auth_headers: dict):
    resp = db_client.get("/api/v1/users/me/items", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == [{"item_id": "Foo", "owner": "alice"}]


def test_me_with_invalid_token(db_client: TestClient):
    """伪造 token 应 401。"""
    resp = db_client.get("/api/v1/users/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert resp.status_code == 401
