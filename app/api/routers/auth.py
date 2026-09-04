"""认证路由：OAuth2 密码模式登录，签发 JWT。

认证相关的工具函数（哈希、JWT、当前用户依赖）位于 app/core/security.py，
便于在 users 路由的 /me 端点中复用，避免循环导入。
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import authenticate_user, create_access_token
from app.db.session import get_db
from app.schemas.auth import Token

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/token", response_model=Token, summary="登录获取令牌")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """OAuth2 密码模式登录，返回 JWT。

    Swagger UI 右上角 "Authorize" 按钮即调用本接口换取 token，
    后续请求会自动携带 `Authorization: Bearer <token>`。
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")
