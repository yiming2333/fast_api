"""应用冒烟测试：根路径、模板、OpenAPI 文档、404 处理。"""

from fastapi.testclient import TestClient


def test_read_root(client: TestClient):
    """根路径返回 Hello 响应。"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, FastAPI!"}


def test_health_check_healthy(client: TestClient):
    """/health 检查 DB 连通性，SQLite 内存库可用时返回 healthy。"""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["checks"]["api"] == "ok"
    assert body["checks"]["db"] == "ok"


def test_hello_page(client: TestClient):
    """Jinja2 模板渲染返回 HTML。"""
    response = client.get("/hello/world")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Hello, world!" in response.text


def test_openapi_docs_available(client: TestClient):
    """Swagger UI 与 OpenAPI schema 可访问。"""
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert schema.json()["info"]["title"] == "我的 API"


def test_unknown_route_returns_custom_404(client: TestClient):
    """覆盖后的 HTTPException 处理器对 404 返回统一错误结构。"""
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.json()


def test_process_time_header(client: TestClient):
    """中间件为每个响应追加 X-Process-Time。"""
    response = client.get("/")
    assert "x-process-time" in response.headers
