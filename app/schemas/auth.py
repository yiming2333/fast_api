"""JWT 认证相关的 schema 与数据模型。"""

from pydantic import BaseModel


class Token(BaseModel):
    """OAuth2 令牌响应。"""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """从 JWT payload 中解析出的数据。"""

    username: str | None = None


class User(BaseModel):
    """对外暴露的用户信息。"""

    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    """数据库中存储的用户（含密码哈希）。"""

    hashed_password: str
