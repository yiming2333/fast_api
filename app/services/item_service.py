"""商品服务 —— Item CRUD 的业务逻辑。

从 app.api.routers.items_db 抽出，统一事务边界与错误翻译。
路由层只做参数解析 + 调用 service + 响应序列化。
"""

from contextlib import asynccontextmanager

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.item import Item as ItemORM
from app.schemas.item_db import ItemCreate, ItemUpdate


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------
def _db_error(exc: Exception) -> HTTPException:
    """把数据库错误翻译成用户能看懂的 HTTP 错误。

    内部错误详情只写日志，返回给客户端的是脱敏后的通用提示。
    """
    if isinstance(exc, OperationalError):
        logger.error("数据库连接失败: %s", exc)
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库服务暂时不可用，请稍后重试",
        )
    if isinstance(exc, IntegrityError):
        logger.warning("数据完整性冲突: %s", exc)
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="数据冲突，可能是重复记录",
        )
    logger.exception("未知数据库错误: %s", exc)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="服务器内部错误",
    )


@asynccontextmanager
async def _db_transaction(db: AsyncSession):
    """统一写操作的事务边界：异常时自动 rollback 并翻译为 HTTP 错误。

    - IntegrityError → 400 数据冲突
    - 其他 SQLAlchemyError → rollback + _db_error
    """
    try:
        yield
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="数据冲突，可能是重复记录",
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise _db_error(exc) from exc


async def _get_item_or_404(db: AsyncSession, item_id: int) -> ItemORM:
    """按 ID 查询商品，不存在则抛 404。"""
    try:
        stmt = select(ItemORM).where(ItemORM.id == item_id)
        obj = (await db.execute(stmt)).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise _db_error(exc) from exc

    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在"
        )
    return obj


# ---------------------------------------------------------------------------
# 对外服务
# ---------------------------------------------------------------------------
async def list_items(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    name: str | None = None,
) -> tuple[list[ItemORM], int]:
    """分页查询商品，支持按名称模糊过滤。返回 (items, total)。"""
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

    return list(rows), total


async def get_item(db: AsyncSession, item_id: int) -> ItemORM:
    """按 ID 获取商品；不存在抛 404。"""
    return await _get_item_or_404(db, item_id)


async def create_item(db: AsyncSession, payload: ItemCreate) -> ItemORM:
    """创建新商品。"""
    obj = ItemORM(**payload.model_dump())
    db.add(obj)
    async with _db_transaction(db):
        await db.commit()
        await db.refresh(obj)
    return obj


async def update_item(
    db: AsyncSession, item_id: int, payload: ItemCreate
) -> ItemORM:
    """全量替换商品字段（PUT 语义），不存在抛 404。"""
    obj = await _get_item_or_404(db, item_id)
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    async with _db_transaction(db):
        await db.commit()
        await db.refresh(obj)
    return obj


async def patch_item(
    db: AsyncSession, item_id: int, payload: ItemUpdate
) -> ItemORM:
    """只更新请求体里提供的字段（PATCH 语义），不存在抛 404。"""
    obj = await _get_item_or_404(db, item_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    async with _db_transaction(db):
        await db.commit()
        await db.refresh(obj)
    return obj


async def delete_item(db: AsyncSession, item_id: int) -> None:
    """按 ID 删除商品，不存在抛 404。"""
    obj = await _get_item_or_404(db, item_id)
    async with _db_transaction(db):
        await db.delete(obj)
        await db.commit()
