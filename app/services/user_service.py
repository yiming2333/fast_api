"""用户服务 —— 用户列表与创建的业务逻辑。

从 app.api.routers.users 抽出，便于复用（如 CLI 脚本、其他路由）与单测。
路由层只做参数解析 + 调用 service + 响应序列化。
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import get_password_hash
from app.models.user import UserORM
from app.schemas.user import UserCreate


async def list_users(db: AsyncSession) -> list[UserORM]:
    """返回全部用户。"""
    result = await db.execute(select(UserORM))
    return list(result.scalars().all())


async def create_user(db: AsyncSession, user: UserCreate) -> UserORM:
    """创建用户：查重 + 哈希密码 + 提交事务。

    Raises:
        HTTPException 400: 用户名已存在或写入失败。
    """
    # 检查用户名是否已存在
    existing = await db.execute(
        select(UserORM).where(UserORM.username == user.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    obj = UserORM(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password),
    )
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
    except Exception as exc:
        await db.rollback()
        logger.warning("创建用户失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="创建用户失败",
        ) from exc
    return obj
