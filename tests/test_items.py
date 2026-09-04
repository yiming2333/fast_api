"""商品路由测试：CRUD、字段过滤、路径参数校验。"""

import pytest
from fastapi.testclient import TestClient


# ===== 列表 =====
def test_list_items_default(client: TestClient):
    """默认分页返回前 10 条。"""
    resp = client.get("/api/v1/demo/items/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3  # fake_items_db 共 3 条


def test_list_items_pagination(client: TestClient):
    """skip/limit 正确切片。"""
    assert len(client.get("/api/v1/demo/items/?skip=1").json()) == 2
    assert len(client.get("/api/v1/demo/items/?skip=1&limit=1").json()) == 1


def test_list_items_skip_negative_rejected(client: TestClient):
    """skip < 0 应被校验拒绝（422）。"""
    assert client.get("/api/v1/demo/items/?skip=-1").status_code == 422


def test_list_items_limit_zero_rejected(client: TestClient):
    """limit 必须 >= 1。"""
    assert client.get("/api/v1/demo/items/?limit=0").status_code == 422


# ===== 详情 =====
def test_read_item_basic(client: TestClient):
    """获取商品详情，带可选查询参数 q。"""
    resp = client.get("/api/v1/demo/items/1", params={"q": "hello"})
    assert resp.status_code == 200
    assert resp.json() == {"item_id": 1, "q": "hello"}


def test_read_item_without_q(client: TestClient):
    assert client.get("/api/v1/demo/items/5").json() == {"item_id": 5, "q": None}


def test_read_item_42_raises_404(client: TestClient):
    """item_id == 42 触发 HTTPException(404)。"""
    resp = client.get("/api/v1/demo/items/42")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_read_item_43_returns_custom_headers(client: TestClient):
    """item_id == 43 返回带自定义响应头的 JSONResponse。"""
    resp = client.get("/api/v1/demo/items/43")
    assert resp.status_code == 200
    assert resp.json() == {"item_id": 43}
    assert resp.headers["x-custom-header"] == "custom-header-value"


def test_read_item_id_must_be_int(client: TestClient):
    """非整数 item_id 应 422。"""
    assert client.get("/api/v1/demo/items/abc").status_code == 422


def test_read_item_id_must_be_positive(client: TestClient):
    """item_id 必须 >= 1。"""
    assert client.get("/api/v1/demo/items/0").status_code == 422


# ===== 创建/更新 =====
def test_create_item_success(client: TestClient):
    """POST 创建商品返回 201 并回显数据。"""
    payload = {"name": "Foo", "price": 35.4, "tags": ["a", "b"]}
    resp = client.post("/api/v1/demo/items/", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Foo"
    assert body["price"] == 35.4
    assert body["tags"] == ["a", "b"]


def test_create_item_validation_failure(client: TestClient):
    """price <= 0 或 name 为空应被拒绝。"""
    assert client.post("/api/v1/demo/items/", json={"name": "", "price": 1}).status_code == 422
    assert client.post("/api/v1/demo/items/", json={"name": "x", "price": 0}).status_code == 422
    assert client.post("/api/v1/demo/items/", json={"name": "x"}).status_code == 422  # 缺 price


def test_update_item(client: TestClient):
    """PUT 更新商品，回显新名称。"""
    resp = client.put("/api/v1/demo/items/7", json={"name": "Bar", "price": 9.9})
    assert resp.status_code == 200
    assert resp.json() == {"item_id": 7, "item_name": "Bar"}


# ===== 字段过滤 =====
def test_read_item_no_tax(client: TestClient):
    """baz 商品不含 tax 字段。"""
    resp = client.get("/api/v1/demo/items/baz/no-tax")
    assert resp.status_code == 200
    assert "tax" not in resp.json()


def test_read_item_no_tax_not_found(client: TestClient):
    resp = client.get("/api/v1/demo/items/unknown/no-tax")
    assert resp.status_code == 404


def test_read_item_filtered_only_name_desc(client: TestClient):
    """response_model_include 限制只返回 name/description。"""
    resp = client.get("/api/v1/demo/items/filtered/foo")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) <= {"name", "description"}


def test_read_item_filtered_unset_excluded(client: TestClient):
    """foo 未设置 description，exclude_unset 后不应出现 description。"""
    body = client.get("/api/v1/demo/items/filtered/foo").json()
    assert "description" not in body
    assert body["name"] == "Foo"
