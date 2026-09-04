"""文件上传路由。

演示三种文件接收方式：
- UploadFile（推荐，流式读取，适合大文件）
- bytes = File()（一次性读入内存，仅适合小文件）
- 保存到磁盘
"""

import os
import shutil

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter(prefix="/demo/files", tags=["演示(文件)"])


@router.get("/{file_path:path}", summary="解析文件路径")
async def read_file(file_path: str):
    """演示 path 类型参数（可包含斜杠）。"""
    return {"file_path": file_path}


@router.post("/upload", summary="上传单个文件（UploadFile）")
async def create_upload_file(file: UploadFile | None = None):
    """上传单个文件，返回文件元信息。"""
    if not file:
        return {"message": "没有上传文件"}
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": file.size,
    }


@router.post("/uploads", summary="上传多个文件")
async def create_upload_files(files: list[UploadFile]):
    """上传多个文件，返回文件名列表。"""
    return {"filenames": [file.filename for file in files]}


@router.post("/raw", summary="上传原始字节文件")
async def create_file(file: bytes = File()):
    """接收文件的原始字节数据。"""
    return {"file_size": len(file)}


@router.post("/save", summary="保存上传的文件到磁盘")
async def save_upload_file(file: UploadFile):
    """将上传的文件保存到 uploads 目录。"""
    os.makedirs(settings.upload_dir, exist_ok=True)
    dest = os.path.join(settings.upload_dir, file.filename)
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return JSONResponse(
        status_code=201,
        content={"filename": file.filename, "message": "文件上传成功"},
    )
