"""安全模块：密码哈希、JWT 签发/校验、当前用户依赖。

将认证相关的可复用逻辑从路由层剥离，便于：
- 在多个路由（auth/users）中复用 get_current_active_user
- 单元测试时通过 dependency_overrides 替换为 mock 用户
- 后续替换为其他认证方案时只改这一处
"""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.db.session import fake_users_db
from app.schemas.auth import User, UserInDB

# 密码哈希工具（bcrypt）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 方案：tokenUrl 必须与实际登录路由一致，
# 否则 Swagger UI 的 Authorize 按钮会请求错误的 URL。
# 登录路由为 POST /api/v1/auth/token（见 routers/auth.py）。
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/token"
)


# ===== 密码 =====
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码。"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希。"""
    return pwd_context.hash(password)


# ===== 用户 =====
def get_user(db: dict, username: str) -> UserInDB | None:
    """从数据库获取用户。"""
    if username in db:
        return UserInDB(**db[username])
    return None


def authenticate_user(db: dict, username: str, password: str):
    """验证用户凭据，成功返回用户，失败返回 False。"""
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


# ===== JWT =====
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建 JWT 访问令牌。"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """从令牌中解析当前用户（依赖函数）。"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user(fake_users_db, username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """获取当前活跃用户（被禁用的用户会被拒绝）。"""
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已被禁用")
    return current_user
