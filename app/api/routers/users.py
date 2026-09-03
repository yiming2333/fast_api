"""用户路由：用户管理与当前登录用户相关接口。

遵循 REST 约定：
- GET    /users/        用户列表
- POST   /users/        创建用户（响应脱敏，不含密码）
- GET    /users/me      当前登录用户信息（需认证）
- GET    /users/me/items 当前用户的条目（需认证）
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import get_current_active_user
from app.schemas.auth import User
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/", summary="用户列表")
async def list_users():
    """返回示例用户列表。"""
    return [{"username": "Rick"}, {"username": "Morty"}]


@router.post("/", response_model=UserOut, summary="创建用户")
async def create_user(user: UserCreate):
    """创建用户。

    函数接收 UserCreate（含密码），但响应使用 UserOut（不含密码），
    避免敏感信息出现在 API 响应中。
    """
    return {"id": 1, **user.model_dump(exclude={"password"})}


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
