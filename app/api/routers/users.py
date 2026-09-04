"""用户路由：用户管理与当前登录用户相关接口。

遵循 REST 约定：
- GET    /users/        用户列表
- POST   /users/        创建用户（响应脱敏，不含密码）
- GET    /users/me      当前登录用户信息（需认证）
- GET    /users/me/items 当前用户的条目（需认证）
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import get_current_active_user, get_password_hash
from app.db.session import get_db
from app.models.user import UserORM
from app.schemas.auth import User
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/", response_model=list[UserOut], summary="用户列表")
async def list_users(db: Annotated[AsyncSession, Depends(get_db)]):
    """返回用户列表。"""
    result = await db.execute(select(UserORM))
    users = result.scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="创建用户")
async def create_user(
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """创建用户，密码自动哈希存储。

    函数接收 UserCreate（含密码），但响应使用 UserOut（不含密码），
    避免敏感信息出现在 API 响应中。
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
        )
    return UserOut.model_validate(obj)


@router.get("/me", response_model=User, summary="获取当前登录用户信息")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """获取当前登录用户信息（需要认证）。"""
    return current_user


@router.get("/me/items", summary="获取当前用户的条目")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """获取当前用户的条目（需要认证）。"""
    return [{"item_id": "Foo", "owner": current_user.username}]
