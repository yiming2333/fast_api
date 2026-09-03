"""SQLAlchemy CRUD 测试（/api/v1/items/db/*）。

每个测试函数使用独立的 SQLite 内存库（由 db_client fixture 提供），
不依赖真实 MySQL 即可跑通。
"""

import allure
from fastapi.testclient import TestClient

BASE = "/api/v1/items/db"


@allure.epic("商品管理")
@allure.feature("DB 持久化 CRUD")
class _AllureMarkers:
    """Allure 分组标记占位类（不被 pytest 收集，因其名字不以 Test 开头）。"""


def test_list_items_empty(db_client: TestClient):
    """列表查询 —— 空库返回 total=0。"""
    allure.dynamic.story("列表查询")
    resp = db_client.get(f"{BASE}/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["skip"] == 0


def test_create_item_success(db_client: TestClient):
    """创建商品返回 201 + 完整数据（含自增 id）。"""
    allure.dynamic.story("创建商品")
    resp = db_client.post(
        f"{BASE}/",
        json={"name": "Laptop", "price": 999.9, "description": "Powerful"},
        headers={"X-API-Key": "secret-key"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["name"] == "Laptop"
    assert body["price"] == 999.9
    assert body["description"] == "Powerful"
    assert body["created_at"] is not None


def test_create_item_requires_api_key(db_client: TestClient):
    """创建需要 X-API-Key，缺失则 422（FastAPI 对 Header 必填校验）。"""
    allure.dynamic.story("创建商品")
    resp = db_client.post(f"{BASE}/", json={"name": "x", "price": 1})
    assert resp.status_code == 422


def test_create_item_wrong_api_key(db_client: TestClient):
    """错误的 API Key 返回 400。"""
    allure.dynamic.story("创建商品")
    resp = db_client.post(
        f"{BASE}/",
        json={"name": "x", "price": 1},
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 400


def test_create_item_validation(db_client: TestClient):
    """price <= 0 / name 为空 / 缺字段 → 422。"""
    allure.dynamic.story("创建商品")
    assert db_client.post(f"{BASE}/", json={"name": "", "price": 1},
                         headers={"X-API-Key": "secret-key"}).status_code == 422
    assert db_client.post(f"{BASE}/", json={"name": "x", "price": 0},
                         headers={"X-API-Key": "secret-key"}).status_code == 422
    assert db_client.post(f"{BASE}/", json={"name": "x"},
                         headers={"X-API-Key": "secret-key"}).status_code == 422


def test_get_item(db_client: TestClient):
    """创建后按 id 获取。"""
    allure.dynamic.story("获取商品")
    create = db_client.post(
        f"{BASE}/",
        json={"name": "Mouse", "price": 29.9},
        headers={"X-API-Key": "secret-key"},
    )
    item_id = create.json()["id"]
    resp = db_client.get(f"{BASE}/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Mouse"


def test_get_item_not_found(db_client: TestClient):
    """不存在返回 404（被自定义 HTTPException 处理器包装为 error 字段）。"""
    allure.dynamic.story("获取商品")
    resp = db_client.get(f"{BASE}/999")
    assert resp.status_code == 404
    assert "商品不存在" in resp.json()["error"]


def test_list_items_pagination(db_client: TestClient):
    """分页 + 按名称过滤。"""
    allure.dynamic.story("列表查询")
    for i in range(5):
        db_client.post(
            f"{BASE}/",
            json={"name": f"Item-{i}", "price": (i + 1) * 10},
            headers={"X-API-Key": "secret-key"},
        )

    # 默认 limit=20
    resp = db_client.get(f"{BASE}/")
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 5

    # limit=2, skip=1
    resp = db_client.get(f"{BASE}/?limit=2&skip=1")
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["skip"] == 1

    # 按名称过滤（模糊）
    resp = db_client.get(f"{BASE}/?name=Item-0")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Item-0"


def test_put_item(db_client: TestClient):
    """PUT 全量替换。"""
    allure.dynamic.story("更新商品")
    create = db_client.post(
        f"{BASE}/",
        json={"name": "Old", "price": 1.0, "description": "desc"},
        headers={"X-API-Key": "secret-key"},
    )
    item_id = create.json()["id"]

    resp = db_client.put(
        f"{BASE}/{item_id}",
        json={"name": "New", "price": 99.0},  # 没有 description → 被替换为 None
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New"
    assert body["price"] == 99.0
    assert body["description"] is None  # 旧值被清空


def test_put_item_not_found(db_client: TestClient):
    allure.dynamic.story("更新商品")
    resp = db_client.put(
        f"{BASE}/999",
        json={"name": "x", "price": 1},
    )
    assert resp.status_code == 404


def test_patch_item(db_client: TestClient):
    """PATCH 只更新提供的字段。"""
    allure.dynamic.story("更新商品")
    create = db_client.post(
        f"{BASE}/",
        json={"name": "Keep", "price": 1.0, "description": "Original"},
        headers={"X-API-Key": "secret-key"},
    )
    item_id = create.json()["id"]

    resp = db_client.patch(
        f"{BASE}/{item_id}",
        json={"price": 99.0},  # 只改 price
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Keep"  # 未变
    assert body["price"] == 99.0  # 已更新
    assert body["description"] == "Original"  # 未变


def test_patch_item_not_found(db_client: TestClient):
    allure.dynamic.story("更新商品")
    resp = db_client.patch(
        f"{BASE}/999",
        json={"name": "x"},
    )
    assert resp.status_code == 404


def test_delete_item(db_client: TestClient):
    """删除返回 204，之后再 GET 应为 404。"""
    allure.dynamic.story("删除商品")
    create = db_client.post(
        f"{BASE}/",
        json={"name": "Del", "price": 1.0},
        headers={"X-API-Key": "secret-key"},
    )
    item_id = create.json()["id"]

    resp = db_client.delete(f"{BASE}/{item_id}")
    assert resp.status_code == 204
    assert resp.content == b""

    resp = db_client.get(f"{BASE}/{item_id}")
    assert resp.status_code == 404


def test_delete_item_not_found(db_client: TestClient):
    allure.dynamic.story("删除商品")
    resp = db_client.delete(f"{BASE}/999")
    assert resp.status_code == 404


def test_create_item_default_tax_none(db_client: TestClient):
    """tax 未提供时为 None。"""
    allure.dynamic.story("创建商品")
    resp = db_client.post(
        f"{BASE}/",
        json={"name": "NoTax", "price": 10.0},
        headers={"X-API-Key": "secret-key"},
    )
    assert resp.status_code == 201
    assert resp.json()["tax"] is None
