"""演示用的内存假数据 —— 不依赖真实数据库。

这些数据仅用于展示 FastAPI 特性（请求头、Cookie、依赖注入等），
真实业务 CRUD 请走 app/models + app/db/session 的 SQLAlchemy 路径。
"""

from passlib.context import CryptContext

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
