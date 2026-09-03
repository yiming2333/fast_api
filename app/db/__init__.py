"""数据访问层入口：SQLAlchemy ORM + 假数据聚合。"""

from .fake_data import fake_items_db, fake_users_db, items_db, pwd_context
from .session import Base, close_engine, get_db, get_engine, get_session_maker, init_db

__all__ = [
    # ORM / 引擎
    "Base",
    "get_db",
    "get_engine",
    "get_session_maker",
    "init_db",
    "close_engine",
    # 假数据
    "fake_items_db",
    "fake_users_db",
    "items_db",
    "pwd_context",
]
