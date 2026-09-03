"""商品路由：演示 RESTful CRUD。

路由命名遵循 REST 约定：
- GET    /items/            列表
- POST   /items/            创建
- GET    /items/{item_id}   详情
- PUT    /items/{item_id}   更新
- GET    /items/{id}/no-tax 派生视图
- GET    /items/filtered/{id} 字段过滤示例
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse

from app.db.session import items_db, fake_items_db
from app.schemas.item import Item

router = APIRouter(prefix="/items", tags=["商品管理"])


@router.get("/", summary="商品列表", description="支持分页查询商品列表")
async def list_items(skip: int = Query(default=0, ge=0), limit: int = Query(default=10, ge=1)):
    """分页返回商品列表。"""
    return fake_items_db[skip : skip + limit]


@router.get("/{item_id}", summary="获取商品信息", response_description="商品信息对象")
async def read_item(
    item_id: Annotated[int, Path(ge=1, description="商品ID")],
    q: Annotated[str | None, Query(description="搜索关键词")] = None,
):
    """根据商品 ID 获取商品的详细信息。

    - **item_id**: 商品的唯一标识符
    - **q**: 可选的搜索关键词
    """
    if item_id == 42:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    content = {"item_id": item_id}
    headers = {"X-Custom-Header": "custom-header-value"}
    if item_id == 43:
        return JSONResponse(content=content, headers=headers)
    return {"item_id": item_id, "q": q}


@router.post("/", status_code=status.HTTP_201_CREATED, summary="创建商品")
async def create_item(item: Item):
    """创建新商品，接收 JSON 请求体。"""
    return item.model_dump()


@router.put("/{item_id}", summary="更新商品")
async def update_item(item_id: Annotated[int, Path(ge=1)], item: Item):
    """更新指定商品，同时使用路径参数和请求体。"""
    return {"item_id": item_id, "item_name": item.name}


@router.get("/{item_id}/no-tax", response_model=Item, response_model_exclude={"tax"}, summary="获取不含税的商品")
async def read_item_no_tax(item_id: str):
    """返回商品信息，但不包含 tax 字段。"""
    if item_id not in items_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return items_db[item_id]


@router.get("/filtered/{item_id}", response_model=Item, response_model_exclude_unset=True,
            response_model_include={"name", "description"}, summary="字段过滤示例")
async def read_item_filtered(item_id: str):
    """演示 response_model_exclude_unset + response_model_include。"""
    if item_id not in items_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return items_db[item_id]
