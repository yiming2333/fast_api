"""示例路由测试：覆盖各类 FastAPI 特性演示端点。"""

import io

from fastapi.testclient import TestClient


# ===== 复合模型 =====
def test_create_offer_nested(client: TestClient):
    """Offer 包含多个 Item，每个 Item 可包含 Image。"""
    payload = {
        "name": "Bundle",
        "price": 100.0,
        "items": [
            {"name": "i1", "price": 30, "image": {"url": "http://x.com/a.png", "name": "a"}},
            {"name": "i2", "price": 40, "tags": ["x", "x"], "tags1": ["x", "x"]},
        ],
    }
    resp = client.post("/api/v1/examples/models/offers", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Bundle"
    # tags1 是 set，去重后转 list
    assert body["items"][1]["tags1"] == ["x"]


def test_create_multiple_images(client: TestClient):
    """请求体为模型列表。"""
    resp = client.post(
        "/api/v1/examples/models/images",
        json=[
            {"url": "http://x.com/1.png", "name": "1"},
            {"url": "http://x.com/2.png", "name": "2"},
        ],
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_create_index_weights(client: TestClient):
    """请求体为 dict[int, float]。"""
    resp = client.post("/api/v1/examples/models/index-weights", json={"1": 0.5, "2": 0.5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["1"] == 0.5


def test_create_index_weights_invalid_value_type(client: TestClient):
    """值非 float 应 422。"""
    resp = client.post("/api/v1/examples/models/index-weights", json={"1": "not-a-number"})
    assert resp.status_code == 422


# ===== 路径与查询参数 =====
def test_path_validation(client: TestClient):
    """item_id >= 1，size 在 (0, 10.5) 之间。"""
    resp = client.get("/api/v1/examples/params/path/3", params={"size": 5.0})
    assert resp.status_code == 200
    assert resp.json() == {"item_id": 3, "size": 5.0}


def test_path_validation_id_too_small(client: TestClient):
    assert client.get("/api/v1/examples/params/path/0").status_code == 422


def test_path_validation_size_out_of_range(client: TestClient):
    assert client.get("/api/v1/examples/params/path/1", params={"size": 11}).status_code == 422


def test_multi_query(client: TestClient):
    """同名查询参数收集为列表。"""
    resp = client.get("/api/v1/examples/params/multi-query", params=[("q", "a"), ("q", "b")])
    assert resp.status_code == 200
    assert resp.json() == {"q": ["a", "b"]}


def test_validated_query_fixedquery(client: TestClient):
    """正则 ^fixedquery$ 校验通过。"""
    resp = client.get("/api/v1/examples/params/validated-query", params={"item-query": "fixedquery"})
    assert resp.status_code == 200
    assert resp.json()["q"] == "fixedquery"


def test_validated_query_pattern_mismatch(client: TestClient):
    """不匹配 pattern 应 422。"""
    resp = client.get("/api/v1/examples/params/validated-query", params={"item-query": "nope"})
    assert resp.status_code == 422


def test_optional_query_with_q(client: TestClient):
    resp = client.get("/api/v1/examples/params/optional-query/abc", params={"q": "hi"})
    assert resp.status_code == 200
    assert resp.json() == {"item_id": "abc", "q": "hi"}


def test_optional_query_without_q(client: TestClient):
    assert client.get("/api/v1/examples/params/optional-query/abc").json() == {"item_id": "abc"}


def test_bool_query_short_true(client: TestClient):
    """short=true 返回精简响应。"""
    resp = client.get("/api/v1/examples/params/bool-query/x", params={"short": "true"})
    assert resp.status_code == 200
    assert resp.json() == {"item_id": "x"}


def test_bool_query_short_false(client: TestClient):
    resp = client.get("/api/v1/examples/params/bool-query/x", params={"short": "false"})
    assert resp.json() == {"item_id": "x", "description": "这是一段很长的描述"}


def test_required_query_missing(client: TestClient):
    """needy 必选查询参数缺失应 422。"""
    assert client.get("/api/v1/examples/params/required-query/x").status_code == 422


def test_required_query_provided(client: TestClient):
    resp = client.get("/api/v1/examples/params/required-query/x", params={"needy": "v"})
    assert resp.status_code == 200
    assert resp.json() == {"item_id": "x", "needy": "v"}


# ===== 请求头与 Cookie =====
def test_read_user_agent(client: TestClient):
    resp = client.get("/api/v1/examples/headers/user-agent", headers={"User-Agent": "pytest"})
    assert resp.json() == {"User-Agent": "pytest"}


def test_read_x_token_multi(client: TestClient):
    # 同名 header 必须用 list[tuple] 形式传入，dict 会合并重复键
    resp = client.get(
        "/api/v1/examples/headers/x-token",
        headers=[("X-Token", "a"), ("X-Token", "b")],
    )
    assert resp.json() == {"X-Token values": ["a", "b"]}


def test_read_x_uid_multi(client: TestClient):
    resp = client.get(
        "/api/v1/examples/headers/x-uid",
        headers=[("X-Uid", "1"), ("X-Uid", "2")],
    )
    assert resp.json() == {"X-Uid values": ["1", "2"]}


def test_read_session_cookie(client: TestClient):
    resp = client.get("/api/v1/examples/cookies/session", cookies={"session_token": "abc"})
    assert resp.json() == {"session_token": "abc"}


def test_read_headers_and_cookies(client: TestClient):
    resp = client.get(
        "/api/v1/examples/headers-cookies",
        headers={"User-Agent": "ua"},
        cookies={"session_token": "st", "ads_id": "ad"},
    )
    body = resp.json()
    assert body == {"User-Agent": "ua", "Session-Token": "st", "Ads-ID": "ad"}


# ===== 异常与响应 =====
def test_redirect(client: TestClient):
    """重定向到 /api/v1/items/。"""
    resp = client.get("/api/v1/examples/responses/redirect", follow_redirects=False)
    assert resp.status_code in (301, 302, 303, 307, 308)
    assert resp.headers["location"].endswith("/api/v1/items/")


def test_unicorn_normal(client: TestClient):
    resp = client.get("/api/v1/examples/responses/unicorns/sweetie")
    assert resp.status_code == 200
    assert resp.json() == {"unicorn_name": "sweetie"}


def test_unicorn_exception(client: TestClient):
    """name=yolo 触发自定义异常处理器，返回 418。"""
    resp = client.get("/api/v1/examples/responses/unicorns/yolo")
    assert resp.status_code == 418
    assert "Oops" in resp.json()["message"]


def test_http_exception_with_dict_detail(client: TestClient):
    """item_id=invalid 返回字典格式的 detail（被自定义处理器字符串化）。"""
    resp = client.get("/api/v1/examples/responses/http-exception/invalid")
    assert resp.status_code == 400
    # 自定义 HTTPException 处理器把 detail 字符串化放入 "error"
    assert "INVALID_ID" in resp.json()["error"]


def test_header_error_with_custom_header(client: TestClient):
    """HTTPException 携带自定义响应头。"""
    resp = client.get("/api/v1/examples/responses/header-error/invalid")
    assert resp.status_code == 404
    assert resp.headers.get("x-error") == "There goes my error"


def test_header_error_normal(client: TestClient):
    resp = client.get("/api/v1/examples/responses/header-error/ok")
    assert resp.status_code == 200
    assert resp.json() == {"item": "ok"}


def test_custom_json_response(client: TestClient):
    resp = client.get("/api/v1/examples/responses/custom/99")
    assert resp.status_code == 200
    assert resp.json() == {"item_id": 99}
    assert resp.headers["x-custom-header"] == "custom-header-value"


# ===== 依赖注入 =====
def test_dependency_common_items(client: TestClient):
    resp = client.get(
        "/api/v1/examples/dependencies/common/items",
        params={"q": "kw", "skip": 5, "limit": 20},
    )
    assert resp.status_code == 200
    assert resp.json() == {"q": "kw", "skip": 5, "limit": 20}


def test_dependency_common_users(client: TestClient):
    resp = client.get("/api/v1/examples/dependencies/common/users")
    assert resp.status_code == 200
    assert resp.json() == {"q": None, "skip": 0, "limit": 100}


def test_dependency_class(client: TestClient):
    resp = client.get(
        "/api/v1/examples/dependencies/class",
        params={"q": "x", "skip": 1, "limit": 2},
    )
    assert resp.status_code == 200
    assert resp.json() == {"q": "x", "skip": 1, "limit": 2}


def test_dependency_sub_query_admin(client: TestClient):
    """q=admin 经子依赖链处理后追加 (checked)。"""
    resp = client.get("/api/v1/examples/dependencies/sub", params={"q": "admin"})
    assert resp.status_code == 200
    assert resp.json() == {"q": "admin (checked)"}


def test_dependency_sub_query_other(client: TestClient):
    resp = client.get("/api/v1/examples/dependencies/sub", params={"q": "user"})
    assert resp.json() == {"q": "user"}


def test_dependency_api_key_protected_ok(client: TestClient):
    """携带正确 X-API-Key 通过。"""
    resp = client.get(
        "/api/v1/examples/dependencies/api-key-protected",
        headers={"X-API-Key": "secret-key"},
    )
    assert resp.status_code == 200
    assert resp.json() == [{"item": "Foo"}]


def test_dependency_api_key_protected_missing(client: TestClient):
    """缺少 X-API-Key 应 422（Header 必填）。"""
    assert client.get("/api/v1/examples/dependencies/api-key-protected").status_code == 422


def test_dependency_api_key_protected_wrong(client: TestClient):
    """X-API-Key 错误应 400。"""
    resp = client.get(
        "/api/v1/examples/dependencies/api-key-protected",
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 400


def test_dependency_route_protected(client: TestClient):
    resp = client.get(
        "/api/v1/examples/dependencies/route-protected",
        headers={"X-API-Key": "secret-key"},
    )
    assert resp.status_code == 200
    assert resp.json() == [{"user": "Bar"}]


def test_dependency_yield_db(client: TestClient):
    """yield 依赖提供数据库句柄。"""
    resp = client.get("/api/v1/examples/dependencies/yield-db")
    assert resp.status_code == 200
    assert resp.json() == {"db": "database_connection"}
