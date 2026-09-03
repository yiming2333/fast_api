"""SQLAlchemy 版 Item CRUD 路由。

路径：/api/v1/items/db/... （保留旧路由 /api/v1/items/... 作为内存字典演示）
职责：完整 REST 语义 —— list / create / get / update / delete
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import verify_api_key
from app.db.session import get_db
from app.models.item import Item as ItemORM
from app.schemas.item_db import ItemCreate, ItemListOut, ItemOut, ItemUpdate

router = APIRouter(prefix="/items/db", tags=["商品(DB)"])


def _db_error(exc: Exception) -> HTTPException:
    """把数据库错误翻译成用户能看懂的 HTTP 错误。

    - OperationalError → 503 Service Unavailable（MySQL 连不上 / 密码错 / 库不存在）
    - IntegrityError   → 400 Bad Request（唯一约束冲突等）
    - 其他            → 500 Internal Server Error
    """
    hint = "请检查 .env 中的 DB_HOST / DB_PASSWORD / DB_NAME 配置"
    if isinstance(exc, OperationalError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"数据库连接失败：{hint} — {exc}",
        )
    if isinstance(exc, IntegrityError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"数据完整性错误：{exc}",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"数据库错误：{exc}",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_model=ItemListOut, summary="商品列表（分页）")
async def list_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(default=0, ge=0, description="偏移量"),
    limit: int = Query(default=20, ge=1, le=100, description="每页数量"),
    name: str | None = Query(default=None, description="按名称模糊过滤"),
):
    """分页查询商品，支持按名称过滤。"""
    try:
        stmt = select(ItemORM)
        total_stmt = select(func.count(ItemORM.id))
        if name:
            like = f"%{name}%"
            stmt = stmt.where(ItemORM.name.like(like))
            total_stmt = total_stmt.where(ItemORM.name.like(like))

        total = (await db.execute(total_stmt)).scalar_one()
        stmt = stmt.offset(skip).limit(limit).order_by(ItemORM.id.desc())
        rows = (await db.execute(stmt)).scalars().all()
    except SQLAlchemyError as exc:
        raise _db_error(exc) from exc

    return ItemListOut(items=[ItemOut.model_validate(r) for r in rows], total=total, skip=skip, limit=limit)


@router.get("/{item_id}", response_model=ItemOut, summary="获取单个商品")
async def get_item(
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """按 ID 获取商品；不存在返回 404。"""
    try:
        stmt = select(ItemORM).where(ItemORM.id == item_id)
        row = (await db.execute(stmt)).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise _db_error(exc) from exc

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
    return ItemOut.model_validate(row)


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
    """创建新商品。需要 X-API-Key: secret-key 请求头。"""
    obj = ItemORM(**payload.model_dump())
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"数据冲突：{exc}")
    except SQLAlchemyError as exc:
        await db.rollback()
        raise _db_error(exc) from exc
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
    try:
        stmt = select(ItemORM).where(ItemORM.id == item_id)
        obj = (await db.execute(stmt)).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise _db_error(exc) from exc

    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")

    for k, v in payload.model_dump().items():
        setattr(obj, k, v)

    try:
        await db.commit()
        await db.refresh(obj)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"数据冲突：{exc}")
    except SQLAlchemyError as exc:
        await db.rollback()
        raise _db_error(exc) from exc
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
    try:
        stmt = select(ItemORM).where(ItemORM.id == item_id)
        obj = (await db.execute(stmt)).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise _db_error(exc) from exc

    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)

    try:
        await db.commit()
        await db.refresh(obj)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"数据冲突：{exc}")
    except SQLAlchemyError as exc:
        await db.rollback()
        raise _db_error(exc) from exc
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
    try:
        stmt = select(ItemORM).where(ItemORM.id == item_id)
        obj = (await db.execute(stmt)).scalar_one_or_none()
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
        await db.delete(obj)
        await db.commit()
    except HTTPException:
        raise
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"数据冲突：{exc}")
    except SQLAlchemyError as exc:
        await db.rollback()
        raise _db_error(exc) from exc

    return None
