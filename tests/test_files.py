"""文件上传路由测试。"""

import io

from fastapi.testclient import TestClient


def test_read_file_path(client: TestClient):
    """:path 参数可匹配包含斜杠的路径。"""
    resp = client.get("/api/v1/files/some/deep/path.txt")
    assert resp.status_code == 200
    assert resp.json() == {"file_path": "some/deep/path.txt"}


def test_upload_single_file_metadata(client: TestClient):
    """UploadFile 返回文件名、MIME 类型、大小。"""
    content = b"hello world"
    resp = client.post(
        "/api/v1/files/upload",
        files={"file": ("note.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "note.txt"
    assert body["content_type"] == "text/plain"
    assert body["size"] == len(content)


def test_upload_no_file(client: TestClient):
    """未上传文件返回提示信息。"""
    resp = client.post("/api/v1/files/upload")
    assert resp.status_code == 200
    assert resp.json() == {"message": "没有上传文件"}


def test_upload_multiple_files(client: TestClient):
    """批量上传返回文件名列表。"""
    resp = client.post(
        "/api/v1/files/uploads",
        files=[
            ("files", ("a.txt", io.BytesIO(b"1"), "text/plain")),
            ("files", ("b.txt", io.BytesIO(b"2"), "text/plain")),
        ],
    )
    assert resp.status_code == 200
    assert resp.json()["filenames"] == ["a.txt", "b.txt"]


def test_upload_raw_bytes(client: TestClient):
    """bytes=File() 接收原始字节。"""
    resp = client.post(
        "/api/v1/files/raw",
        files={"file": ("data.bin", io.BytesIO(b"x" * 100), "application/octet-stream")},
    )
    assert resp.status_code == 200
    assert resp.json() == {"file_size": 100}


def test_save_upload_file(client: TestClient, tmp_path, monkeypatch):
    """保存的文件应写入配置的上传目录。"""
    # 把上传目录重定向到 pytest 提供的临时目录，避免污染仓库
    from app.core import config as config_module
    from app.core.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    # lru_cache 不影响 settings 实例属性，直接打补丁即可

    resp = client.post(
        "/api/v1/files/save",
        files={"file": ("saved.txt", io.BytesIO(b"saved-content"), "text/plain")},
    )
    assert resp.status_code == 201
    saved = tmp_path / "saved.txt"
    assert saved.exists()
    assert saved.read_bytes() == b"saved-content"
