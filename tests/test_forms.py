"""表单路由测试。"""

from fastapi.testclient import TestClient


def test_form_login(client: TestClient):
    """表单登录回显用户名密码（演示用）。"""
    resp = client.post(
        "/api/v1/demo/forms/login",
        data={"username": "alice", "password": "secret"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"username": "alice", "password": "secret"}


def test_form_create_item(client: TestClient):
    """表单字段含必填/可选/数值校验。"""
    resp = client.post(
        "/api/v1/demo/forms/items",
        data={"name": "Foo", "description": "bar", "price": "9.9"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"name": "Foo", "description": "bar", "price": 9.9}


def test_form_create_item_optional_description(client: TestClient):
    resp = client.post("/api/v1/demo/forms/items", data={"name": "Foo", "price": "1"})
    assert resp.status_code == 200
    assert resp.json()["description"] is None


def test_form_create_item_price_must_be_positive(client: TestClient):
    assert client.post(
        "/api/v1/demo/forms/items", data={"name": "x", "price": "0"}
    ).status_code == 422


def test_form_create_item_missing_required(client: TestClient):
    """缺 name 或 price 应 422。"""
    assert client.post("/api/v1/demo/forms/items", data={"name": "x"}).status_code == 422
    assert client.post("/api/v1/demo/forms/items", data={"price": "1"}).status_code == 422


def test_form_with_file(client: TestClient):
    """表单字段与上传文件混合提交。"""
    resp = client.post(
        "/api/v1/demo/forms/items-with-file",
        data={"name": "Foo", "description": "desc"},
        files={"file": ("note.txt", b"hi", "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Foo"
    assert body["description"] == "desc"
    assert body["filename"] == "note.txt"


def test_form_with_file_optional(client: TestClient):
    """未上传文件时不返回 filename 字段。"""
    resp = client.post(
        "/api/v1/demo/forms/items-with-file",
        data={"name": "Foo"},
    )
    assert resp.status_code == 200
    assert "filename" not in resp.json()
