"""数据访问层。

本项目暂未接入真实数据库，使用内存字典作为示例存储，
方便直接运行与测试。真实场景下应替换为 SQLAlchemy / Tortoise 等 ORM。
"""

from passlib.context import CryptContext
from pydantic import BaseModel

# 密码哈希工具（bcrypt），所有用户密码都应经过哈希后存储
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---- 商品示例数据 ----
items_db: dict[str, dict] = {
    "foo": {"name": "Foo", "price": 50.2},
    "bar": {"name": "Bar", "description": "The bartenders", "price": 62, "tax": 20.2},
    "baz": {"name": "Baz", "description": None, "price": 50.2, "tax": 10.5, "tags": []},
}

# 用于演示分页查询的“数据库”
fake_items_db: list[dict] = [
    {"item_name": "Foo"},
    {"item_name": "Bar"},
    {"item_name": "Baz"},
]


# ---- 用户示例数据（带密码哈希） ----
fake_users_db: dict[str, dict] = {
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": pwd_context.hash("secret"),
        "disabled": False,
    },
}


class DBSession(BaseModel):
    """演示用的 DB 句柄类型，真实场景应替换为 ORM Session。"""

    connection: str = "database_connection"
