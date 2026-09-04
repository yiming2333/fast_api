"""用户路由：用户管理与当前登录用户相关接口。

遵循 REST 约定：
- GET    /users/        用户列表
- POST   /users/        创建用户（响应脱敏，不含密码）
- GET    /users/me      当前登录用户信息（需认证）
- GET    /users/me/items 当前用户的条目（需认证）

路由层只做参数解析 + 调用 service + 响应序列化；
业务逻辑（查重、哈希、提交）在 app.services.user_service。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.schemas.auth import User
from app.schemas.user import UserCreate, UserOut
from app.services import user_service

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/", response_model=list[UserOut], summary="用户列表")
async def list_users(db: Annotated[AsyncSession, Depends(get_db)]):
    """返回用户列表。"""
    users = await user_service.list_users(db)
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
    obj = await user_service.create_user(db, user)
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
