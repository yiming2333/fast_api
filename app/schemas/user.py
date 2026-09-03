"""用户相关的 Pydantic 模型。

遵循“输入/输出分离”的最佳实践：创建用户时接收密码，
但响应模型不包含密码，避免敏感信息泄露。
"""

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """用户基础字段。"""

    username: str
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """创建用户时的输入模型（包含密码）。"""

    password: str


class UserOut(UserBase):
    """返回用户信息时的输出模型（不含密码）。"""

    id: int
