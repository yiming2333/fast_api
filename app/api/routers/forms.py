"""表单路由。

演示 Form 数据接收，包括必填/可选字段、数值校验以及表单+文件混合提交。
"""

from fastapi import APIRouter, File, Form, UploadFile

router = APIRouter(prefix="/forms", tags=["表单"])


@router.post("/login", summary="表单登录示例")
async def login(
    username: str = Form(...),
    password: str = Form(...),
):
    """接收表单字段用户名与密码。"""
    return {"username": username, "password": password}


@router.post("/items", summary="通过表单创建商品")
async def create_item(
    name: str = Form(..., description="必填"),
    description: str | None = Form(None, description="可选，默认 None"),
    price: float = Form(..., gt=0, description="必填，必须大于 0"),
):
    """演示必填/可选表单字段及数值校验。"""
    return {"name": name, "description": description, "price": price}


@router.post("/items-with-file", summary="表单+文件混合提交")
async def create_item_with_file(
    name: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    """同时接收表单字段与上传文件。"""
    result = {"name": name, "description": description}
    if file:
        result["filename"] = file.filename
    return result
