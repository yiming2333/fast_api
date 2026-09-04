"""文件上传路由。

演示三种文件接收方式：
- UploadFile（推荐，流式读取，适合大文件）
- bytes = File()（一次性读入内存，仅适合小文件）
- 保存到磁盘

安全校验：
- 文件类型白名单（基于 content_type）
- 文件大小上限（防止撑爆磁盘 / 内存）
"""

import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter(prefix="/demo/files", tags=["演示(文件)"])

# 允许上传的文件类型白名单
ALLOWED_TYPES = {
    "text/plain",
    "image/png",
    "image/jpeg",
    "application/pdf",
}
# 单文件大小上限（10MB）
MAX_SIZE = 10 * 1024 * 1024


def _validate_file(file: UploadFile) -> bytes:
    """校验文件类型与大小，返回文件内容。

    - 类型不在白名单 → 400
    - 超过大小上限   → 413
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}",
        )
    content = file.file.read() if hasattr(file, "file") else None
    if content is None:
        # 兜底：UploadFile.file.read() 不可用时走 await read()
        raise HTTPException(status_code=400, detail="文件内容读取失败")
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="文件过大（上限 10MB）")
    return content


@router.get("/{file_path:path}", summary="解析文件路径")
async def read_file(file_path: str):
    """演示 path 类型参数（可包含斜杠）。"""
    return {"file_path": file_path}


@router.post("/upload", summary="上传单个文件（UploadFile）")
async def create_upload_file(file: UploadFile | None = None):
    """上传单个文件，返回文件元信息。"""
    if not file:
        return {"message": "没有上传文件"}
    content = _validate_file(file)
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content),
    }


@router.post("/uploads", summary="上传多个文件")
async def create_upload_files(files: list[UploadFile]):
    """上传多个文件，返回文件名列表。"""
    for file in files:
        _validate_file(file)
    return {"filenames": [file.filename for file in files]}


@router.post("/raw", summary="上传原始字节文件")
async def create_file(file: bytes = File()):
    """接收文件的原始字节数据。"""
    if len(file) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="文件过大（上限 10MB）")
    return {"file_size": len(file)}


@router.post("/save", summary="保存上传的文件到磁盘")
async def save_upload_file(file: UploadFile):
    """将上传的文件保存到 uploads 目录。"""
    content = _validate_file(file)
    os.makedirs(settings.upload_dir, exist_ok=True)
    dest = os.path.join(settings.upload_dir, file.filename)
    with open(dest, "wb") as buffer:
        buffer.write(content)
    return JSONResponse(
        status_code=201,
        content={"filename": file.filename, "message": "文件上传成功"},
    )
