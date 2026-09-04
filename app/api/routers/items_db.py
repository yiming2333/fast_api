"""SQLAlchemy 版 Item CRUD 路由。

路径：/api/v1/items/db/...
职责：完整 REST 语义 —— list / create / get / update / delete

路由层只做参数解析 + 调用 service + 响应序列化；
业务逻辑（查询、事务、错误翻译）在 app.services.item_service。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import verify_api_key
from app.db.session import get_db
from app.schemas.item_db import ItemCreate, ItemListOut, ItemOut, ItemUpdate
from app.services import item_service

router = APIRouter(prefix="/items/db", tags=["商品(DB)"])


@router.get("/", response_model=ItemListOut, summary="商品列表（分页）")
async def list_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(default=0, ge=0, description="偏移量"),
    limit: int = Query(default=20, ge=1, le=100, description="每页数量"),
    name: str | None = Query(default=None, description="按名称模糊过滤"),
):
    """分页查询商品，支持按名称过滤。"""
    items, total = await item_service.list_items(db, skip=skip, limit=limit, name=name)
    return ItemListOut(
        items=[ItemOut.model_validate(r) for r in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{item_id}", response_model=ItemOut, summary="获取单个商品")
async def get_item(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """按 ID 获取商品；不存在返回 404。"""
    obj = await item_service.get_item(db, item_id)
    return ItemOut.model_validate(obj)


@router.post(
    "/",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建商品",
    dependencies=[Depends(verify_api_key)],  # 演示：创建需要 API Key
)
async def create_item(
    payload: ItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """创建新商品。需要 X-API-Key: *** 请求头。"""
    obj = await item_service.create_item(db, payload)
    return ItemOut.model_validate(obj)


@router.put(
    "/{item_id}",
    response_model=ItemOut,
    summary="全量更新商品",
)
async def update_item(
    item_id: int,
    payload: ItemCreate,  # PUT 语义：全量替换
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """全量替换商品字段（PUT 语义），不存在返回 404。"""
    obj = await item_service.update_item(db, item_id, payload)
    return ItemOut.model_validate(obj)


@router.patch(
    "/{item_id}",
    response_model=ItemOut,
    summary="部分更新商品",
)
async def patch_item(
    item_id: int,
    payload: ItemUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """只更新请求体里提供的字段（PATCH 语义）。"""
    obj = await item_service.patch_item(db, item_id, payload)
    return ItemOut.model_validate(obj)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除商品",
)
async def delete_item(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """按 ID 删除商品，不存在返回 404。"""
    await item_service.delete_item(db, item_id)
    return None
